"""Remainder addition (unit addition:mobile-device-management-l2):
spec integrity and substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 50 (Mobile Device Management
(MDM), CMMC L2). The previously uncategorized fork (Ivanti /
Ivanti Neurons for MDM (Formerly MobileIron)) was spec'd under
the group's EXISTING 16-family taxonomy applied verbatim — the
additions extractor parses the TAXONOMY literal out of the
shipped ``scratch/extract.py`` via ``ast`` (parsed, never
executed, never re-typed) and reproduces the original fork's
shipped claim table exactly (16 claims, evidence included)
before tagging the newcomer.

The newcomer claims **0 families** — a zero-claim fork. Its
marketplace description is a genuine mobile-device / unified
endpoint management description (device validation, automatic
provisioning of enterprise settings, app and content delivery,
zero-trust enforcement, mobile threat defense), and the group's
taxonomy — defined from the founding fork's telecom expense
management prose — contains no device-management family at all,
so the raw hit count is 0 across all 16 families and there is
nothing for the wording-artifact corrections to correct. The
group total stays 16 claims (1 of 2 forks claiming; every family
at 1 of 2). Both census citations verify verbatim against the
stored (whitespace-normalized) description and both tag
nothing: verification is not a claim, and census classification
is not a claim either, in either direction.

The category's named absences, against the newcomer: device
enrollment & provisioning and mobile app delivery are asserted
in the fork's own words and retire as *substance* findings
(they survive as *claims* absences — no family exists for
them); the enforcement half of device policy & compliance
enforcement is asserted in substance; remote wipe/lock and
device location survive in both senses (zero tokens each).

Neither claim nor absence extends the core: ``src/`` is
byte-identical. The core-delta question was considered head-on
(ADDENDUM section 3): the one records-shaped candidate, a
device registry, is barred by the group's founding privacy
invariant — the inventory shape is pinned to service records
with no field that can hold a device identifier — and no claim
requires it, so the device-management plane is registered
Extended, not bolted onto this core. The substrate cases
exercise the shipped core in the newcomer's operator shape: an
agency mobility estate held as service records (opaque refs
only), provisioning moved only by fulfilled service orders, and
a funded budget whose availability is derived at read (Core 8 —
that assertion trips the group's signature ``_available_cents``
drill by exactly one; see tests/README.md). The fork's
provisioning engine, zero-trust validation, and threat-defense
engine themselves are Extended (ADDENDUM section 5), not
implemented, and nothing in these cases claims them.
"""

import json
import os
import re
import unittest

import mdm_helpers as H
from mdm.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "FR2505553757",  # Turning Point Global Solutions, L.L.C —
                     # Network Inventory and Optimization
                     # Solution (NiOS®)
]
UNIT_ORDER = [
    "F1507116930",   # Ivanti — Ivanti Neurons for MDM
                     # (Formerly MobileIron)
]

ALL_FAMILIES = [
    "telecom_service_orders",
    "configurable_workflow",
    "inventory_management",
    "bill_validation",
    "dispute_management",
    "financial_management",
    "budget_visibility",
    "budget_alerts",
    "chargebacks",
    "reporting",
    "lifecycle_single_view",
    "web_portal",
    "data_integration",
    "analytics",
    "api_access",
    "cloud_hosting_platform",
]

ORIGINAL_CLAIM_COUNTS = {
    "FR2505553757": 16,
}

# The literal claim table for the addition: zero claims.
EXPECTED_CLAIMS = {
    "F1507116930": [],
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    return dump[3]["data"]["fedRAMPData"]["data"]["ProductsMap"][fork_id]


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description and citation accounting,
    near-miss pins, named-absence accounting."""

    def test_sheet_count_and_order(self):
        """2 sheets: the shipped singleton untouched in place,
        then the addition in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork,
        extending exactly this group."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:mobile-device-management-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"],
                         "mobile-device-management-l2")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[1:]],
                         unit["fork_ids"])

    def test_original_claim_table_stands(self):
        """The original fork's shipped claim table stands
        exactly (16 claims, one per family)."""
        specs = _load_specs()
        for fork_id, count in ORIGINAL_CLAIM_COUNTS.items():
            self.assertEqual(
                len(_sheet(specs, fork_id)["functions_claimed"]), count,
                fork_id)

    def test_literal_claim_table_zero_claims(self):
        """The addition fork claims exactly nothing: its
        functions_claimed list is empty — the pinned zero-claim
        table, not a missing one."""
        sheet = _sheet(_load_specs(), "F1507116930")
        self.assertEqual(
            [c["function_id"] for c in sheet["functions_claimed"]],
            EXPECTED_CLAIMS["F1507116930"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_zero_claim_family_set_is_the_whole_taxonomy(self):
        """The newcomer's zero-claim set is all 16 families of
        the group's taxonomy — the taxonomy contains no
        device-management family, so a genuine MDM description
        has nothing to fire."""
        sheet = _sheet(_load_specs(), "F1507116930")
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_group_totals(self):
        """The group total stays 16 claims; 1 of 2 forks claims.
        Every family stands at exactly 1 of 2 (the founding
        fork only)."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 16)
        zero = [s["fork_id"] for s in specs if not s["functions_claimed"]]
        self.assertEqual(zero, ["F1507116930"])
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(
                    c["function_id"], []).append(s["fork_id"])
        self.assertEqual(len(by_family), 16)
        for fid in ALL_FAMILIES:
            self.assertEqual(by_family[fid], ["FR2505553757"], fid)

    def test_addition_tier_fields(self):
        """The addition is FedRAMP Moderate / Certified / L2 /
        SaaS / Government Community Cloud, so the group stays
        single-tier and the Moderate baseline is unchanged. Its
        source record carries no business categories; forks.json
        files it 'Uncategorized (none in source)'; the DeadRamp
        category is the census proposal, Mobile Device
        Management (MDM)."""
        sheet = _sheet(_load_specs(), "F1507116930")
        self.assertEqual(sheet["vendor"], "Ivanti")
        self.assertEqual(sheet["product"],
                         "Ivanti Neurons for MDM (Formerly MobileIron)")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Mobile Device Management (MDM)")
        with open(os.path.join(_REPO_ROOT, "forks.json")) as fh:
            forks = json.load(fh)
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        row = next(r for r in rows
                   if r["source_url"].rstrip("/").endswith("F1507116930"))
        self.assertEqual(row["category"], "Uncategorized (none in source)")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description under the group's
        original convention (whitespace normalized to single
        spaces, stripped) — the same convention the shipped
        singleton sheet follows."""
        sheet = _sheet(_load_specs(), "F1507116930")
        expected = re.sub(
            r"\s+", " ",
            _raw_product("F1507116930")["service_desc"]).strip()
        self.assertEqual(sheet["description"], expected)

    def test_census_citations_verify_and_tag_nothing(self):
        """Citation accounting: both of the fork's census
        citations verify as strict verbatim substrings of the
        stored description — and the fork claims nothing, so
        both citations tag nothing. The census classified by
        substance ('Unified endpoint / mobile device
        management'); the claim pass reads the same text for
        the taxonomy's pattern phrases and finds none.
        Verification is not a claim, and classification is not
        a claim either, in either direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        cites = census["F1507116930"]["citations"]
        self.assertEqual(len(cites), 2)
        sheet = _sheet(_load_specs(), "F1507116930")
        for c in cites:
            self.assertIn(c, sheet["description"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the fork's source record
        carries no certified-services block and no
        scope-exclusion segment. Its operating-system list
        (iOS, Android, Windows 10, macOS, Zebra, Oculus)
        enumerates the platforms the fork's OWN product
        manages — its own supported surface, not a catalogue
        of third-party hosted applications. Matched text is
        the full text; the raw hit count is zero, so nothing
        was removed."""
        self.assertEqual(
            _raw_product("F1507116930")["certified_services"], [])
        desc = _sheet(_load_specs(), "F1507116930")["description"]
        self.assertIn("such as iOS, Android, Windows 10, macOS, "
                      "Zebra and Oculus", desc)
        for phrase in ("not authorized", "not included",
                       "out of scope"):
            self.assertNotIn(phrase, desc.lower())

    def test_named_absence_accounting(self):
        """The five category named absences against the
        newcomer's own words (ADDENDUM section 2):
        provisioning/onboarding substance present (absence
        retires in substance, survives at claim level — no
        family exists); app/content delivery substance
        present; policy-enforcement substance present with no
        'policy' token; wipe, lock, and location tokens
        entirely absent (absences survive in both senses)."""
        desc = _sheet(_load_specs(), "F1507116930")["description"]
        low = desc.lower()
        # Substance present, in the fork's own words:
        self.assertIn("automatically provisions enterprise settings", low)
        self.assertIn("simplest onboarding", low)
        self.assertIn("applications and content delivery", low)
        self.assertIn("privacy enforcement", low)
        self.assertIn("validates the device", low)
        # Tokens absent — the surviving absences:
        self.assertNotIn("wipe", low)
        self.assertNotIn("lock", low)
        self.assertNotIn("location", low)
        self.assertNotIn("gps", low)
        self.assertNotIn("track", low)
        self.assertNotIn("policy", low)
        self.assertNotIn("policies", low)
        self.assertNotIn("catalog", low)

    def test_near_miss_pins_ivanti(self):
        """Ivanti: the device-management substance is present
        in its own words; the TEM taxonomy's pattern phrases
        are absent, so every family stays at its shipped count
        for this fork."""
        desc = _sheet(_load_specs(), "F1507116930")["description"]
        low = desc.lower()
        # Substance present (gaps, ADDENDUM sections 2 and 5):
        self.assertIn("zero trust", low)
        self.assertIn("threat defense", low)
        self.assertIn("single console", low)
        self.assertIn("byod", low)
        # Family pattern phrases absent:
        self.assertNotIn("single-pane", low)
        self.assertNotIn("telecom lifecycle management", low)
        self.assertNotIn("reporting", low)
        self.assertNotIn("inventory", low)
        self.assertNotIn("analytics", low)
        self.assertNotIn("system alerts", low)
        self.assertNotIn("hosted on amazon web services", low)
        self.assertNotIn("multi-tenant", low)
        self.assertNotIn("web-based portal", low)
        self.assertNotIn("data integration", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the operator shape
    the newcomer presupposes — an agency mobility estate — through
    the records forms the shipped substrate holds."""

    def test_ivanti_mobility_estate_budget_derivation(self):
        """Ivanti shape: a mobility service line is held in the
        inventory registry under an opaque ref (Core 2 — the
        record carries exactly the pinned ten keys, none of
        which can hold a phone number, IMEI, serial, or any
        device identifier), and the estate's funded budget reads
        obligated / spent / available derived at read, never
        stored (Core 8 — the availability assertions trip the
        group's signature _available_cents drill by exactly
        one). The fork's provisioning and management engines
        that would act on real devices are Extended — nothing
        here touches a device."""
        store, org = H.make_store()
        item = H.make_inventory(
            store, org, ref="MOB-LINE-1", service_kind="mobility",
            label="Field mobility line", plan_ref="PLAN-UEM-1",
            monthly_recurring_cents=12_500)
        self.assertEqual(item["service_kind"], "mobility")
        self.assertEqual(len(item.keys()), 10)
        joined = "_".join(sorted(item.keys()))
        for forbidden in ("phone", "imei", "serial", "device",
                          "location"):
            self.assertNotIn(forbidden, joined)
        H.make_funded_budget(store, org)
        budget = store.get_budget(H.MEMBER, "bud-1")
        self.assertEqual(budget["obligated_cents"], H.OBLIGATED_CENTS)
        self.assertEqual(budget["spent_cents"], H.SPENT_CENTS)
        self.assertEqual(budget["available_cents"], H.AVAILABLE_CENTS)
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["budget_available_cents"],
                         H.AVAILABLE_CENTS)

    def test_ivanti_provisioning_order_lifecycle(self):
        """Ivanti shape: a mobility line's provisioning state
        moves only through fulfilled service orders (Core 3):
        a suspend order requested by the member cannot be
        decided by its own requester (AC-5), is approved by a
        second member, and only fulfillment suspends the line;
        a restore order returns it to active. Registering a
        workflow definition for the provisioning process
        changes no state (Core 4 — the registry never
        executes). The carrier- and device-facing execution of
        any of this is Extended."""
        store, org = H.make_store()
        item = H.make_inventory(
            store, org, ref="MOB-LINE-2", service_kind="mobility",
            label="Executive mobility line", plan_ref="PLAN-UEM-1",
            monthly_recurring_cents=9_900)
        workflow = store.create_workflow(
            H.MEMBER, org["id"], "Provisioning steps",
            ["request", "approve", "fulfill"])
        self.assertEqual(workflow["steps"],
                         ["request", "approve", "fulfill"])
        item = store.get_inventory_item(H.MEMBER, item["id"])
        self.assertEqual(item["provisioning_state"], "active")
        order = store.create_order(
            H.MEMBER, org["id"], "suspend", "Suspend lost-device line",
            inventory_id=item["id"])
        with self.assertRaises(PermissionDenied):
            store.decide_order(H.MEMBER, order["id"], True)
        store.decide_order(H.STAFF, order["id"], True)
        store.fulfill_order(H.MEMBER, order["id"])
        item = store.get_inventory_item(H.MEMBER, item["id"])
        self.assertEqual(item["provisioning_state"], "suspended")
        restore = store.create_order(
            H.MEMBER, org["id"], "restore", "Replacement device issued",
            inventory_id=item["id"])
        store.decide_order(H.STAFF, restore["id"], True)
        store.fulfill_order(H.MEMBER, restore["id"])
        item = store.get_inventory_item(H.MEMBER, item["id"])
        self.assertEqual(item["provisioning_state"], "active")


if __name__ == "__main__":
    unittest.main()
