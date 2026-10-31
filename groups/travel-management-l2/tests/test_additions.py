"""Remainder addition (unit addition:travel-management-l2): spec
integrity and substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 55 (Travel Management,
CMMC L2). The previously uncategorized fork (mLINQS /
mLINQS Hosting Service) was spec'd under the group's EXISTING
9-family taxonomy applied verbatim — the additions extractor
parses the TAXONOMY literal out of the shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed,
never re-typed) and reproduces the original fork's shipped
claim table exactly (9 claims) before tagging the newcomer.
The original extractor carries no CORRECTIONS literal: its
wording-artifact corrections are prose in
``scratch/ARTIFACTS.md``, applied as recorded judgment.

The newcomer claims **0 families** — a zero-claim fork. Its
marketplace description is an employee-relocation listing:
eight sentences about processing employee moves and automating
relocation policy, in which none of the taxonomy's verbatim
patterns (all defined from GO.gov's own suite-list vocabulary)
appears. The raw hit count is 0 across all 9 families. Both
census citations verify verbatim against the description and
tag no family: verification is not a claim, and census
classification is not a claim either, in either direction.

The singleton's checked absences were re-searched against the
newcomer's text and survive in full: no booking or reservation
token, no per-diem token, no reimbursement token, no approval
token, no receipt token. The functions the fork describes in
its own words (relocation processing, relocation policy
automation) are registered as gaps in the ADDENDUM, not built.

The substrate cases exercise the shipped core as the newcomer
would use it: an employee move presupposes the same records
form as a trip — a traveler record of pinned shape, an
authorization decided by someone other than its requester, an
expense report whose total derives at read, and vouchers
capped at that total (Core 2/3/5/8; the voucher assertion
trips the group's signature ``_check_voucher_cap`` drill by
exactly one; see tests/README.md). The relocation-processing
and policy-automation engines themselves are Extended
(ADDENDUM section 5), not implemented, and nothing in these
cases claims them.
"""

import json
import os
import re
import unittest

from travel.errors import ValidationError

from travel_helpers import (DECIDER, MEMBER, make_store, make_traveler)

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "FR2607452240",   # IBM — GO.gov
]
UNIT_ORDER = [
    "F1610037949",    # mLINQS — mLINQS Hosting Service
]

ALL_FAMILIES = [
    "travel_services",
    "expense_services",
    "integration_services",
    "notification_services",
    "reporting_services",
    "travel_expense_operations",
    "security_privacy_compliance",
    "system_of_systems_composition",
    "cloud_hosting_platform",
]

ORIGINAL_CLAIMS = {
    "FR2607452240": [
        "travel_services",
        "expense_services",
        "integration_services",
        "notification_services",
        "reporting_services",
        "travel_expense_operations",
        "security_privacy_compliance",
        "system_of_systems_composition",
        "cloud_hosting_platform",
    ],
}

# The literal claim table for the addition: zero claims.
EXPECTED_CLAIMS = {
    "F1610037949": [],
}

NEWCOMER_SENTENCES = [
    "Since 2004, more than 30 federal agencies have trusted "
    "moveLINQ to process thousands of employee moves annually.",
    "As the first comprehensive, fully functional system designed "
    "expressly for government agencies to manage employee "
    "relocation, that trust is well founded.",
    "Agencies can be confident that every relocation processed "
    "using moveLINQ will be in full compliance.",
    "The software automates FTR, JTR, DSSR, and 6FAM CONUS/OCONUS "
    "relocation policy, and adheres to E-Gov Travel, GSA/OMB "
    "reporting, and Section 508 standards.",
    "Now mLINQS offers its leading relocation management on a "
    "hosted platform.",
    "As with other hosted solutions, this Software as a Service "
    "(SaaS) model provides agencies higher availability at a "
    "lower cost.",
    "Federal managers are able to focus their budgets on business "
    "objectives rather than infrastructure and the need to "
    "predict and meet future capacity.",
    "By leveraging efficiencies attained by hosting multiple "
    "federal agencies, mLINQS Hosting Services provides increased "
    "scalability and flexibility while increasing support "
    "services to customers.",
]


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _raw_products(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("id") == fork_id and "service_desc" in obj:
                found.append(obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(dump)
    return found


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description, census citation accounting,
    near-miss pins, checked-absence accounting."""

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
                    if u["unit_id"] == "addition:travel-management-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "travel-management-l2")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[1:]],
                         unit["fork_ids"])

    def test_original_claim_table_stands(self):
        """The original fork's shipped claim table stands
        exactly (9 claims, one per family, in taxonomy order)."""
        specs = _load_specs()
        sheet = _sheet(specs, "FR2607452240")
        got = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertEqual(got, ORIGINAL_CLAIMS["FR2607452240"])

    def test_literal_claim_table_zero_claims(self):
        """The addition fork claims exactly nothing: its
        functions_claimed list is empty — the pinned zero-claim
        table, not a missing one."""
        sheet = _sheet(_load_specs(), "F1610037949")
        self.assertEqual(
            [c["function_id"] for c in sheet["functions_claimed"]],
            EXPECTED_CLAIMS["F1610037949"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_zero_claim_family_set_is_the_whole_taxonomy(self):
        """The newcomer's zero-claim set is all 9 families of
        the group's taxonomy."""
        sheet = _sheet(_load_specs(), "F1610037949")
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_group_totals(self):
        """The group total stays 9 claims; 1 of 2 forks claims.
        Every family stands at exactly 1 (GO.gov)."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 9)
        zero = [s["fork_id"] for s in specs if not s["functions_claimed"]]
        self.assertEqual(zero, ["F1610037949"])
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(c["function_id"], []).append(s["fork_id"])
        self.assertEqual(len(by_family), 9)
        for forks in by_family.values():
            self.assertEqual(forks, ["FR2607452240"])

    def test_addition_tier_fields(self):
        """The addition is FedRAMP Moderate / Certified / L2 /
        SaaS / Government Community Cloud, so the group stays
        single-tier and the Moderate baseline is unchanged. Its
        source record carries no business categories
        (uncategorized in the source); the DeadRamp category is
        the census proposal, Travel Management."""
        sheet = _sheet(_load_specs(), "F1610037949")
        self.assertEqual(sheet["vendor"], "mLINQS")
        self.assertEqual(sheet["product"], "mLINQS Hosting Service")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Travel Management")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description (whitespace-normalized,
        per the group's convention). Two cached records carry
        this ID; their descriptions are byte-identical."""
        records = _raw_products("F1610037949")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["service_desc"],
                         records[1]["service_desc"])
        sheet = _sheet(_load_specs(), "F1610037949")
        self.assertEqual(sheet["description"],
                         " ".join(records[0]["service_desc"].split()))
        self.assertEqual(sheet["description"],
                         " ".join(NEWCOMER_SENTENCES))

    def test_census_citations_verify_and_tag_nothing(self):
        """Citation accounting: both census citations verify as
        verbatim substrings of the description — and neither
        tags a family. The census classified by substance
        ("Employee relocation management under federal travel
        regulations"). Verification is not a claim, and
        classification is not a claim either, in either
        direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == "F1610037949")
        cites = census["citations"]
        self.assertEqual(len(cites), 2)
        sheet = _sheet(_load_specs(), "F1610037949")
        for cite in cites:
            self.assertIn(" ".join(cite.split()), sheet["description"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the fork's source record
        carries no certified-services block, and its text names
        only its own product (moveLINQ) and its own components —
        no catalogue of third-party hosted applications and no
        scope-exclusion segment. Matched text is the full text;
        the raw hit count is zero, so nothing was removed."""
        for record in _raw_products("F1610037949"):
            self.assertEqual(record["certified_services"], [])

    def test_checked_absences_survive(self):
        """The singleton's checked absences, re-searched against
        the newcomer's text at the token level: no booking or
        reservation vocabulary, no per-diem vocabulary, no
        reimbursement vocabulary, no approval vocabulary, no
        receipt vocabulary. All five survive for the enlarged
        group; nothing here retires any of them, because a
        retirement must rest on the fork's own words and these
        words are absent."""
        desc = _sheet(_load_specs(), "F1610037949")["description"]
        low = desc.lower()
        self.assertIsNone(re.search(r"book|reserv|itinerary|flight|"
                                    r"airline|hotel|lodging|rental", low))
        self.assertIsNone(re.search(r"per diem|allowance|rate table", low))
        self.assertIsNone(re.search(r"reimburs|voucher|disburs", low))
        self.assertIsNone(re.search(r"approv|authoriz", low))
        self.assertIsNone(re.search(r"receipt|\bscan\b|\bocr\b", low))

    def test_near_miss_pins_mlinqs(self):
        """mLINQS: relocation substance is present in its own
        words; the taxonomy's operative pattern phrases are
        absent, so every family stays at its shipped count for
        this fork."""
        desc = _sheet(_load_specs(), "F1610037949")["description"]
        low = desc.lower()
        # Substance present (gaps, ADDENDUM sections 2 and 5):
        self.assertIn("process thousands of employee moves", low)
        self.assertIn("manage employee relocation", low)
        self.assertIn("automates ftr, jtr, dssr, and 6fam", low)
        self.assertIn("relocation policy", low)
        self.assertIn("hosted platform", low)
        # Family pattern phrases absent:
        self.assertNotIn("suite of travel", low)
        self.assertNotIn("expense, integration", low)
        self.assertNotIn("integration, notification", low)
        self.assertNotIn("notification, and reporting", low)
        self.assertNotIn("reporting services", low)
        self.assertNotIn("streamline and standardize", low)
        self.assertNotIn("compliance with federal security and "
                         "privacy regulations", low)
        self.assertNotIn("system of systems", low)
        self.assertNotIn("secure hosting environments", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_mlinqs_relocation_expense_flow_and_voucher_cap(self):
        """mLINQS shape: an employee move is processed through
        the records form it presupposes — a traveler record
        (Core 2), a relocation authorization in integer cents
        decided by a member other than its requester (Core 3/4,
        AC-5), an expense report whose items are added while it
        is a draft and whose total derives at read (Core 5/6),
        and vouchers recorded against the approved report up to
        exactly its total, with one cent over rejected whole
        (Core 8 — that assertion trips the group's signature
        voucher-cap drill by exactly one). The relocation
        processing engine itself is Extended; nothing here
        processes a move."""
        store, org = make_store()
        traveler = make_traveler(store, org)
        auth = store.create_authorization(
            MEMBER, org["id"], traveler["id"],
            destination_label="Relocation: Fort Worth, TX",
            purpose="Employee relocation",
            depart_date="2026-07-01", return_date="2026-07-03",
            authorized_cents=900_000)
        store.submit_authorization(MEMBER, auth["id"])
        store.decide_authorization(DECIDER, auth["id"], True,
                                   note="Approved")
        report = store.create_expense_report(
            MEMBER, auth["id"], "Relocation expenses")
        store.add_expense_item(MEMBER, report["id"],
                               "other", 400_000,
                               "2026-07-01")
        store.add_expense_item(MEMBER, report["id"],
                               "lodging", 125_000,
                               "2026-07-02")
        draft_view = store.get_expense_report(MEMBER, report["id"])
        self.assertEqual(draft_view["total_cents"], 525_000)
        store.submit_expense_report(MEMBER, report["id"])
        store.decide_expense_report(DECIDER, report["id"], True,
                                    note="Approved")
        store.record_voucher(MEMBER, report["id"], 400_000)
        store.record_voucher(MEMBER, report["id"], 125_000)
        view = store.get_expense_report(MEMBER, report["id"])
        self.assertEqual(view["reimbursed_cents"], 525_000)
        self.assertEqual(view["remaining_cents"], 0)
        with self.assertRaises(ValidationError):
            store.record_voucher(MEMBER, report["id"], 1)

    def test_mlinqs_traveler_shape_and_derived_views(self):
        """mLINQS shape: the traveler record an employee move
        presupposes is the pinned six-key shape (Core 2 — no
        field can hold a name-bearing identifier beyond the
        label, a document number, or any real personal data),
        and a relocation authorization's trip phase derives at
        read from its dates while the stored-side reads carry
        no derived money keys the substrate does not define
        (Core 3/5, derived-never-stored)."""
        store, org = make_store()
        traveler = make_traveler(store, org)
        self.assertEqual(len(traveler), 6)
        for key in traveler:
            self.assertNotIn(key, ("name", "email", "phone", "ssn",
                                   "dob", "passport", "document_number",
                                   "address", "salary", "grade"))
        auth = store.create_authorization(
            MEMBER, org["id"], traveler["id"],
            destination_label="Relocation: Fort Worth, TX",
            purpose="Employee relocation",
            depart_date="2026-07-01", return_date="2026-07-03",
            authorized_cents=900_000)
        before = store.get_authorization(MEMBER, auth["id"],
                                         as_of="2026-06-15")
        self.assertEqual(before["phase"], "upcoming")
        during = store.get_authorization(MEMBER, auth["id"],
                                         as_of="2026-07-02")
        self.assertEqual(during["phase"], "in_progress")
        after = store.get_authorization(MEMBER, auth["id"],
                                        as_of="2026-07-10")
        self.assertEqual(after["phase"], "completed")


if __name__ == "__main__":
    unittest.main()
