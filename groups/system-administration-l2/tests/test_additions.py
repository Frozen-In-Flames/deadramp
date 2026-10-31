"""Additions coverage: the 8 remainder forks joining this group.

Traces to: DeadRamp remainder unit ``addition:system-administration-l2``
(remainder census in repo-root remainder.json) and ADDENDUM.md.

The additions were spec'd under this group's EXISTING 8-family
taxonomy, applied verbatim (scratch/extract_additions.py imports the
taxonomy from the shipped scratch/extract.py; adjudication and
near-miss record in scratch/ADDITIONS_ARTIFACTS.md). These tests pin
the spec outcome the way the rest of the suite pins the original
fork's claims:

- the specs file holds 9 sheets and the shipped sheet is first and
  unchanged in content (8 claims; the enlarged group totals 9);
- addition membership is exactly the census unit's 8 fork IDs;
- every addition claim is a taxonomy family whose stored evidence
  is a verbatim substring of the fork's own description;
- the claim map is exactly as spec'd (1 claim over 1 fork; 7 forks
  claim zero families -- recorded, not inflated);
- the one claimed family rides its shipped disposition:
  virtualization enablement is Extended (the virtualization engine
  is the CSP's) -- the store exposes no virtualization entry point,
  and what the claimant presupposes in Core is the records
  substrate itself (managed systems and hosted applications,
  known only by opaque references).
"""

import json
import os
import unittest

from sysadmin_helpers import MEMBER, make_store, make_system
from sysadmin.store import SysadminStore

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")

ORIGINAL_ID = "FR2415334644"  # USDA AMPS

ADDITION_IDS = [
    "FR1819254092", "FR1833967442", "FR2000951694", "FR2016131254",
    "F1311252651", "FR2215946050", "F1209041518", "FR2624215150",
]

# The group's taxonomy, verbatim from scratch/extract.py.
TAXONOMY_LABELS = {
    "general_support_system":
        "General Support System (GSS) of operating systems & services",
    "managed_os_and_services":
        "Full management of operating systems & services",
    "application_delivery":
        "Application delivery on the managed platform",
    "third_party_hosting_platform":
        "Operation on third-party CSP hosting platforms",
    "control_inheritance":
        "Control inheritance from the underlying CSP",
    "virtualization_enablement":
        "CSP virtualization of computing environments",
    "high_availability":
        "Highly Available (HA) network, up-time & redundancy",
    "restricted_access":
        "Access restricted to contracting organizations",
}

# The adjudicated claim map (scratch/ADDITIONS_ARTIFACTS.md).
EXPECTED_CLAIMS = {
    "FR1819254092": {"virtualization_enablement"},  # Citrix DaaS
}


def _load_specs():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


class TestAdditionSpecs(unittest.TestCase):
    """Additions spec integrity, traced to ADDENDUM.md sections 1-2."""

    def test_specs_file_has_9_sheets_and_original_first(self):
        """9 sheets total; the shipped sheet leads with its shipped
        8 claims; the enlarged group totals 9 claims."""
        specs = _load_specs()
        self.assertEqual(len(specs), 9)
        self.assertEqual(specs[0]["fork_id"], ORIGINAL_ID)
        self.assertEqual(len(specs[0]["functions_claimed"]), 8)
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 9)

    def test_addition_membership_is_exactly_the_census_unit(self):
        """The appended sheets are exactly the unit's 8 fork IDs,
        each Moderate / L2 / System Administration (census-assigned
        category; forks.json lists them as uncategorized)."""
        specs = _load_specs()
        additions = specs[1:]
        self.assertEqual([s["fork_id"] for s in additions],
                         ADDITION_IDS)
        for s in additions:
            with self.subTest(fork=s["fork_id"]):
                self.assertEqual(s["fedramp_impact_level"], "Moderate")
                self.assertEqual(s["cmmc_tier"], "L2")
                self.assertEqual(s["deadramp_category"],
                                 "System Administration")

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
                                     {"function_id", "function",
                                      "evidence"})

    def test_every_addition_claim_is_taxonomy_and_evidence_verbatim(self):
        """Every claimed function_id is one of the 8 taxonomy
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
        """1 claim over 1 fork; the other 7 additions claim zero
        families under the verbatim taxonomy -- the sheets record
        that plainly instead of inflating near-misses into claims
        (near-miss record: scratch/ADDITIONS_ARTIFACTS.md)."""
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
            sum(1 for v in seen.values() if not v), 7)


class TestAdditionClaimsRideTheUnion(unittest.TestCase):
    """The claimed family maps to its shipped union disposition
    (ADDENDUM.md section 4): no core extension was warranted."""

    def test_virtualization_claim_is_extended_only_no_engine_surface(self):
        """Extended: Virtualization engine. Citrix's claim joins
        AMPS's in the virtualization gap (the engine is the CSP's).
        Honesty pin: the store exposes no virtualization,
        hypervisor, or VM-provisioning entry point through which a
        virtual machine could be created or run -- the family is
        specified in the union, not implemented."""
        for name in ("create_virtual_machine", "provision_vm",
                     "create_vm", "start_hypervisor",
                     "run_hypervisor", "virtualize",
                     "launch_instance", "spin_up_instance",
                     "deploy_workspace", "provision_desktop"):
            self.assertFalse(hasattr(SysadminStore, name), name)

    def test_virtualization_claimant_rides_the_records_substrate(self):
        """Core 2/3: what a virtualization claimant presupposes in
        Core is the records substrate -- the virtualized estate is
        registered as managed systems known only by opaque
        references on an opaque platform reference, with hosted
        applications registered on them. The pinned nine-key
        system shape has no field for a hypervisor, a VM instance
        identifier, or any live-system identifier."""
        store, org = make_store()
        system = make_system(store, org, ref="SYS-VDI-1",
                             label="Virtual desktop host pool",
                             platform_ref="PLAT-VDI")
        self.assertEqual(len(system), 9)
        self.assertEqual(system["platform_ref"], "PLAT-VDI")
        app = store.create_application(
            MEMBER, org["id"], system["id"],
            "APP-WORKSPACE", "Delivered workspace")
        self.assertEqual(app["system_id"], system["id"])


if __name__ == "__main__":
    unittest.main()
