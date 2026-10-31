"""Additions coverage: the 20 remainder forks joining this group.

Traces to: DeadRamp remainder unit ``addition:operations-management-l2``
(REMINDER census in repo-root remainder.json) and ADDENDUM.md.

The additions were spec'd under this group's EXISTING 19-family
taxonomy, applied verbatim (scratch/extract_additions.py; adjudication
and near-miss record in scratch/ADDITIONS_ARTIFACTS.md). These tests pin
the spec outcome the way the rest of the suite pins the original two
forks' claims:

- the specs file holds 22 sheets and the two shipped sheets are first
  and unchanged in content (7 and 13 claims, 27 claims in total);
- addition membership is exactly the census unit's 20 fork IDs;
- every addition claim is a taxonomy family whose stored evidence is
  a verbatim substring of the fork's own description;
- the claim map is exactly as spec'd (7 claims over 6 forks;
  14 forks claim zero families -- recorded, not inflated);
- the claimed families ride the shipped dispositions: workflow
  automation's Core side is the workflow registry (which never
  executes), and integrations is Extended only -- the store exposes
  no connector or execution entry point for it.
"""

import json
import os
import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, fresh_store
from opsmgmt.errors import PermissionDenied
from opsmgmt.store import OpsStore

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")

ORIGINAL_IDS = ["FR2225648574", "FR2619646960"]  # MCSS, TrackVia

ADDITION_IDS = [
    "F1404043549", "AGENCYHUDSAAS", "FR1918442180", "FR1923039219",
    "FR2324454026", "FR1728053006", "FR1816364586", "FR1927682057",
    "FR2129953050", "F1506256801", "FR2102577114", "F1608097919",
    "FR1733061545", "FR1730866868", "FR2000945223", "FR1722532017",
    "FR2130949241", "FR2108649352", "FR2132958724", "FR1730334049",
]

# The group's taxonomy, verbatim from scratch/extract.py.
TAXONOMY_LABELS = {
    "program_operations": "Program & project operations",
    "operational_data": "Operational data & structured records",
    "workflow_automation": "Workflow automation",
    "reporting_intelligence": "Reporting & operational intelligence",
    "asset_management": "Asset & equipment management",
    "inspections_field_ops": "Inspections & field operations",
    "workforce_readiness": "Workforce & mission readiness",
    "safety_compliance": "Safety & compliance management",
    "governance_compliance": "Governance & compliance functions",
    "authorization_services": "Authorization & access services",
    "security_services": "Common security services",
    "network_connectivity": "Network connectivity & platform services",
    "usage_information": "Usage information & metering",
    "policy_enforcement": "Policy enforcement",
    "app_configuration": "Application configuration & deployment",
    "mobile_capabilities": "Mobile capabilities",
    "integrations": "Integrations & interoperability",
    "ai_capability": "AI capability",
    "vendor_management": "Contractor & vendor management",
}

# The adjudicated claim map (scratch/ADDITIONS_ARTIFACTS.md).
EXPECTED_CLAIMS = {
    "FR1918442180": {"workflow_automation"},          # Bizagi
    "FR2324454026": {"workflow_automation"},          # FM:Systems
    "FR1728053006": {"workflow_automation", "integrations"},  # IBM
    "FR1816364586": {"workflow_automation"},          # Ivanti
    "FR2132958724": {"workflow_automation"},          # UiPath
    "FR1730334049": {"workflow_automation"},          # Xerox
}

WORKFLOW_CLAIMANTS = [f for f, fs in EXPECTED_CLAIMS.items()
                      if "workflow_automation" in fs]


def _load_specs():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


class TestAdditionSpecs(unittest.TestCase):
    """Additions spec integrity, traced to ADDENDUM.md sections 1-2."""

    def test_specs_file_has_22_sheets_and_originals_first(self):
        """22 sheets total; the shipped two lead, with their shipped
        claim counts (7 and 13); the enlarged group totals 27 claims."""
        specs = _load_specs()
        self.assertEqual(len(specs), 22)
        self.assertEqual([s["fork_id"] for s in specs[:2]], ORIGINAL_IDS)
        self.assertEqual(len(specs[0]["functions_claimed"]), 7)
        self.assertEqual(len(specs[1]["functions_claimed"]), 13)
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 27)

    def test_addition_membership_is_exactly_the_census_unit(self):
        """The appended sheets are exactly the unit's 20 fork IDs,
        each Moderate / L2 / Operations Management (census-assigned
        category; forks.json lists them as uncategorized)."""
        specs = _load_specs()
        additions = specs[2:]
        self.assertEqual([s["fork_id"] for s in additions], ADDITION_IDS)
        for s in additions:
            with self.subTest(fork=s["fork_id"]):
                self.assertEqual(s["fedramp_impact_level"], "Moderate")
                self.assertEqual(s["cmmc_tier"], "L2")
                self.assertEqual(s["deadramp_category"],
                                 "Operations Management")

    def test_addition_sheets_follow_the_house_schema(self):
        """Each addition sheet carries exactly the shipped sheets'
        key set, and each claim entry exactly
        {function_id, function, evidence}."""
        specs = _load_specs()
        house_keys = set(specs[0].keys())
        self.assertEqual(set(specs[1].keys()), house_keys)
        for s in specs[2:]:
            with self.subTest(fork=s["fork_id"]):
                self.assertEqual(set(s.keys()), house_keys)
                for c in s["functions_claimed"]:
                    self.assertEqual(set(c.keys()),
                                     {"function_id", "function", "evidence"})

    def test_every_addition_claim_is_taxonomy_and_evidence_verbatim(self):
        """Every claimed function_id is one of the 19 taxonomy
        families with the taxonomy's label, and its evidence is a
        verbatim substring of the fork's own description."""
        specs = _load_specs()
        for s in specs[2:]:
            for c in s["functions_claimed"]:
                with self.subTest(fork=s["fork_id"],
                                  function=c["function_id"]):
                    self.assertIn(c["function_id"], TAXONOMY_LABELS)
                    self.assertEqual(c["function"],
                                     TAXONOMY_LABELS[c["function_id"]])
                    self.assertTrue(c["evidence"])
                    self.assertIn(c["evidence"], s["description"])

    def test_addition_claim_map_is_exactly_as_specd(self):
        """7 claims over 6 forks; the other 14 additions claim zero
        families under the verbatim taxonomy -- the sheets record
        that plainly instead of inflating near-misses into claims
        (near-miss record: scratch/ADDITIONS_ARTIFACTS.md)."""
        specs = _load_specs()
        seen = {}
        for s in specs[2:]:
            seen[s["fork_id"]] = {c["function_id"]
                                  for c in s["functions_claimed"]}
        for fid in ADDITION_IDS:
            with self.subTest(fork=fid):
                self.assertEqual(seen[fid],
                                 EXPECTED_CLAIMS.get(fid, set()))
        self.assertEqual(sum(len(v) for v in seen.values()), 7)
        self.assertEqual(
            sum(1 for v in seen.values() if not v), 14)


class TestAdditionClaimsRideTheUnion(unittest.TestCase):
    """Claimed families map to shipped union dispositions (ADDENDUM
    section 3): no core extension was warranted."""

    def test_workflow_automation_claims_ride_the_registry_core(self):
        """Core 7: Workflow registry. Six addition forks claim
        workflow automation; its Core side is the registry -- a
        definition can be registered and versioned per claimant
        shape, registration executes nothing (a matching work order
        keeps its state), and workflow writes stay admin-only (the
        execution engine remains Extended for all seven forks that
        now assert the family)."""
        self.assertEqual(len(WORKFLOW_CLAIMANTS), 6)
        for fid in WORKFLOW_CLAIMANTS:
            with self.subTest(fork=fid):
                store = fresh_store()
                wo = store.create_work_order(
                    OPERATOR, "task", "Addition claimant work")
                wf = store.create_workflow(
                    ADMIN, "auto-" + fid, "task",
                    "on create", "route for review")
                store.update_workflow(
                    wf["id"], ADMIN, action_text="route to queue")
                after = store.get_work_order(wo["id"], OPERATOR)
                self.assertEqual(after["status"], "open")
                self.assertEqual(
                    store.get_workflow(wf["id"], ADMIN)["version"], 2)
                with self.assertRaises(PermissionDenied):
                    store.create_workflow(
                        OPERATOR, "operator-wf", "task", "t", "a")

    def test_integrations_claim_is_extended_only_no_engine_surface(self):
        """Extended: Integrations. IBM's integrations claim joins
        TrackVia's in the connector-engines gap. Honesty pin: the
        store exposes no connector, execution, or sync entry point
        through which an integration could run -- the family is
        specified in the union, not implemented."""
        for name in ("execute_workflow", "run_workflow",
                     "execute", "run_automation", "sync",
                     "connect", "create_integration",
                     "register_integration", "invoke_connector"):
            self.assertFalse(hasattr(OpsStore, name), name)


if __name__ == "__main__":
    unittest.main()
