"""Additions coverage: the 3 remainder forks joining this group.

Traces to: DeadRamp remainder unit ``addition:operations-management-l1``
(census in repo-root remainder.json) and ADDENDUM.md.

The additions were spec'd under this group's EXISTING 19-family
taxonomy (Group 36's, carried verbatim by the shipped singleton pass),
applied verbatim (scratch/additions_extract.py; the taxonomy literal
is parsed out of the shipped scratch/extract.py and asserted
triple-equal to Group 36's before tagging). These tests pin the spec
outcome the way the rest of the suite pins the original fork's sheet:

- the specs file holds 4 sheets and the shipped OpenWater sheet is
  first and unchanged in content (0 claims; the enlarged group
  totals exactly 1 claim);
- addition membership is exactly the census unit's 3 fork IDs;
- every addition claim is a taxonomy family whose stored evidence is
  a verbatim substring of the fork's own description, and every
  census citation verifies verbatim (verification is not a claim:
  all 4 citations tag no family -- Tango's claim rests on a
  different sentence of its certified Reserve surface);
- the claim map is exactly as spec'd (1 claim over 1 fork; SCMC and
  FM:Systems claim zero families -- recorded, not inflated);
- the claimed family rides the shipped disposition: integrations is
  Extended only -- the store exposes no connector or execution
  entry point for it.
"""

import json
import os
import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, fresh_store, make_store
from opsmgmt.errors import PermissionDenied
from opsmgmt.store import OpsStore

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_CENSUS_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

ORIGINAL_IDS = ["FR2113346550"]  # OpenWater

ADDITION_IDS = [
    "FR2017462201",  # Booz Allen Hamilton / SCMC (Prodigo Marketplace)
    "FR1828574469",  # FM:Systems / OpenBlue Employee
    "FR2100740435",  # Tango / Tango (Reserve)
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

# The adjudicated claim map (ADDENDUM.md section 2).
EXPECTED_CLAIMS = {
    "FR2100740435": {"integrations"},  # Tango
}


def _load_specs():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


def _sheet(fid):
    for s in _load_specs():
        if s["fork_id"] == fid:
            return s
    raise AssertionError(fid)


class TestAdditionSpecs(unittest.TestCase):
    """Additions spec integrity, traced to ADDENDUM.md sections 1-2."""

    def test_specs_file_has_4_sheets_and_original_first(self):
        """4 sheets total; the shipped OpenWater sheet leads with its
        shipped claim count (0); the enlarged group totals 1 claim."""
        specs = _load_specs()
        self.assertEqual(len(specs), 4)
        self.assertEqual([s["fork_id"] for s in specs[:1]], ORIGINAL_IDS)
        self.assertEqual(len(specs[0]["functions_claimed"]), 0)
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 1)

    def test_addition_membership_is_exactly_the_census_unit(self):
        """The appended sheets are exactly the unit's 3 fork IDs,
        each LI-SaaS / L1 / Operations Management (census-assigned
        category; forks.json lists them as uncategorized)."""
        specs = _load_specs()
        additions = specs[1:]
        self.assertEqual([s["fork_id"] for s in additions], ADDITION_IDS)
        for s in additions:
            with self.subTest(fork=s["fork_id"]):
                self.assertEqual(s["fedramp_impact_level"], "LI-SaaS")
                self.assertEqual(s["cmmc_tier"], "L1")
                self.assertEqual(s["deadramp_category"],
                                 "Operations Management")

    def test_addition_sheets_follow_the_house_schema(self):
        """Each addition sheet carries exactly the shipped sheet's
        key set, and each claim entry exactly
        {function_id, function, evidence}."""
        specs = _load_specs()
        house_keys = set(specs[0].keys())
        for s in specs[1:]:
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
        for s in specs[1:]:
            for c in s["functions_claimed"]:
                with self.subTest(fork=s["fork_id"],
                                  function=c["function_id"]):
                    self.assertIn(c["function_id"], TAXONOMY_LABELS)
                    self.assertEqual(c["function"],
                                     TAXONOMY_LABELS[c["function_id"]])
                    self.assertTrue(c["evidence"])
                    self.assertIn(c["evidence"], s["description"])

    def test_addition_claim_map_is_exactly_as_specd(self):
        """1 claim over 1 fork (Tango, integrations); SCMC and
        FM:Systems claim zero families under the verbatim taxonomy
        -- the sheets record that plainly instead of inflating
        near-misses into claims (near-miss record: ADDENDUM.md
        section 2). 18 of 19 families stay unclaimed by the
        additions."""
        specs = _load_specs()
        seen = {}
        for s in specs[1:]:
            seen[s["fork_id"]] = {c["function_id"]
                                  for c in s["functions_claimed"]}
        for fid in ADDITION_IDS:
            with self.subTest(fork=fid):
                self.assertEqual(seen[fid],
                                 EXPECTED_CLAIMS.get(fid, set()))
        self.assertEqual(sum(len(v) for v in seen.values()), 1)
        self.assertEqual(
            sum(1 for v in seen.values() if not v), 2)
        claimed = set().union(*seen.values()) if seen else set()
        self.assertEqual(claimed, {"integrations"})
        self.assertEqual(len(set(TAXONOMY_LABELS) - claimed), 18)

    def test_census_citations_verify_verbatim_but_tag_nothing(self):
        """All 4 census citations for the unit's forks are verbatim
        substrings of the forks' own cached descriptions -- and
        none of them is the evidence sentence of any claim
        (verification is not a claim; Tango's integrations claim
        rests on its functionality-list sentence)."""
        with open(_CENSUS_PATH) as fh:
            census = {f["fork_id"]: f for f in json.load(fh)["forks"]}
        total = 0
        for fid in ADDITION_IDS:
            sheet = _sheet(fid)
            evidence = {c["evidence"] for c in sheet["functions_claimed"]}
            for cite in census[fid]["citations"]:
                total += 1
                with self.subTest(fork=fid):
                    self.assertIn(cite, sheet["description"])
                    self.assertNotIn(cite, evidence)
        self.assertEqual(total, 4)

    def test_near_misses_are_recorded_not_claimed(self):
        """Family-adjacent wording that matches no pattern stays
        unclaimed, pinned per fork (ADDENDUM.md section 2):
        SCMC's "right vendors" is not "contractor and vendor
        management" and its "secure cloud infrastructure" is not
        "security services"; FM:Systems' singular "Outlook
        Integration" / "IoT Sensor Integration" are not the plural
        \\bintegrations\\b, its "contactless workflows" are not
        "automated workflows", and "mobile scheduling" is not
        "mobile capabilities"; Tango's "operational data" is not
        "structured data" and its "operational Analytics" matches
        no reporting-intelligence phrase."""
        scmc = _sheet("FR2017462201")
        self.assertIn("right vendors", scmc["description"])
        self.assertIn("secure cloud infrastructure", scmc["description"])
        fm = _sheet("FR1828574469")
        self.assertIn("Outlook Integration", fm["description"])
        self.assertIn("contactless workflows", fm["description"])
        self.assertIn("mobile scheduling", fm["description"])
        tango = _sheet("FR2100740435")
        self.assertIn("operational data", tango["description"])
        self.assertIn("operational Analytics", tango["description"])
        for fid in ("FR2017462201", "FR1828574469"):
            self.assertEqual(_sheet(fid)["functions_claimed"], [])


class TestAdditionSubstrateCases(unittest.TestCase):
    """Each addition fork exercised against the shipped substrate
    (ADDENDUM.md sections 3-4): the records forms its prose
    presupposes already exist; the engines it actually runs are
    gaps, pinned absent where the honesty pin applies."""

    def test_scmc_procurement_records_ride_the_substrate(self):
        """SCMC (0 claims): a vendor organization, a supply project,
        a requisition work order, and an order-volume usage record
        are Core 1/2/4/6 records. The work order's overdue flag is
        derived at read (past due at the later ``now``, not before)
        and never stored -- this case trips the _is_overdue mutant,
        as designed (ADDENDUM.md section 6)."""
        store, _person, _org, _proj = make_store()
        vendor = store.create_organization(
            "Preferred Supply Vendor", OPERATOR, reference="VND-9001")
        program = store.create_project(
            "Healthcare Supply Program", OPERATOR, org_id=vendor["id"])
        wo = store.create_work_order(
            OPERATOR, "task", "Process supply requisition",
            project_id=program["id"], due_at="2020-01-01T00:00:00Z")
        store.record_usage(OPERATOR, program["id"], "orders", 42, "2026-10")
        early = store.get_work_order(wo["id"], OPERATOR,
                                     now="2019-06-01T00:00:00Z")
        self.assertFalse(early["overdue"])
        late = store.get_work_order(wo["id"], OPERATOR,
                                    now="2026-06-01T00:00:00Z")
        self.assertTrue(late["overdue"])
        self.assertNotIn("overdue", store._work_orders[wo["id"]])
        rep = store.report(OPERATOR, now="2026-06-01T00:00:00Z")
        self.assertEqual(rep["work_orders"]["overdue"], 1)
        self.assertEqual(rep["usage"]["by_metric"], {"orders": 42})

    def test_fm_systems_scheduling_is_a_gap_not_a_core_function(self):
        """FM:Systems (0 claims): its headline function -- desk and
        resource scheduling -- has NO taxonomy family (the
        category's standing scheduling absence) and NO records form
        or entry point in the Core: the store exposes no
        reservation/scheduling API. What the substrate does hold is
        the reservable-resource side: an asset record for a room and
        a registered (never executed) workflow definition;
        registering it changes no work order's state, and workflow
        writes stay admin-only."""
        for name in ("create_reservation", "reserve", "schedule",
                     "create_booking", "book_room", "create_schedule"):
            self.assertFalse(hasattr(OpsStore, name), name)
        store = fresh_store()
        room = store.create_asset("Conference Room 4B", OPERATOR,
                                  kind="room")
        self.assertEqual(room["status"], "in_service")
        wo = store.create_work_order(OPERATOR, "task",
                                     "Prepare Room 4B", asset_id=room["id"])
        wf = store.create_workflow(ADMIN, "room-turnover", "task",
                                   "on booking", "notify facilities")
        after = store.get_work_order(wo["id"], OPERATOR)
        self.assertEqual(after["status"], "open")
        self.assertEqual(store.get_workflow(wf["id"], ADMIN)["version"], 1)
        with self.assertRaises(PermissionDenied):
            store.create_workflow(OPERATOR, "operator-wf", "task", "t", "a")

    def test_tango_integrations_claim_is_extended_only(self):
        """Tango (integrations claim): the family is Extended at
        this tier -- the connector-engines gap gains a claimant,
        and the store exposes no connector, integration, or sync
        entry point through which an integration could run. The
        Core side of the claim is Core 10, the REST API surface
        itself. Tango's workplace records (a neighborhood project
        and a facilities work order) ride the substrate, with
        overdue derived at read -- this case also trips the
        _is_overdue mutant, as designed."""
        for name in ("create_integration", "register_integration",
                     "invoke_connector", "connect", "sync",
                     "execute_workflow", "run_workflow"):
            self.assertFalse(hasattr(OpsStore, name), name)
        store, _person, _org, _proj = make_store()
        hood = store.create_project("Neighborhood A Workplaces", OPERATOR)
        wo = store.create_work_order(
            OPERATOR, "general", "Reconfigure hoteling area",
            project_id=hood["id"], due_at="2020-06-01T00:00:00Z")
        view = store.get_work_order(wo["id"], OPERATOR,
                                    now="2026-06-01T00:00:00Z")
        self.assertTrue(view["overdue"])
        self.assertNotIn("overdue", store._work_orders[wo["id"]])


if __name__ == "__main__":
    unittest.main()
