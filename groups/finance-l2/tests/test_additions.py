"""Remainder additions — Finance L2 (unit ``addition:finance-l2``).

Traces to: ADDENDUM.md §§1–3 — the 4 previously uncategorized forks
(Apptio TBM, CGI Momentum, Coupa Spend Management for Federal,
Innovest Trust & Wealth Management) spec'd under the group's
existing 8-family taxonomy applied verbatim, and the substrate
cases each fork's surface exercises against the unchanged Core.

Spec-integrity pins: sheet count / unit order / membership against
``remainder.json``; the literal per-fork claim table (1 new claim:
Coupa ``spend_management``; the other three forks claim zero
families, pinned here rather than hidden); verbatim evidence; the
census citations verified against the sheets' descriptions; the
Coupa evidence re-anchor; and the near-miss pins recorded in
ADDENDUM §2 (Innovest's "multi-currency" is not "multi-tenant";
Apptio's "SaaS provider" is not "SaaS offering").
"""

import json
import os
import re
import unittest

import finance_helpers as H
from finance.errors import ValidationError

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

UNIT_ID = "addition:finance-l2"
UNIT_ORDER = ["F1603157879", "FR2022243058", "F1308202329", "FR1821933307"]
ORIGINALS = ["FR2623848170", "FR2626247309"]

EXPECTED_CLAIMS = {
    "FR2623848170": ["earned_wage_access", "financial_wellness",
                     "api_platform", "hosting_platform"],
    "FR2626247309": ["travel_booking", "travel_management",
                     "spend_management", "reporting"],
    "F1603157879": [],
    "FR2022243058": [],
    "F1308202329": ["spend_management"],
    "FR1821933307": [],
}

COUPA_EVIDENCE = (
    "It covers the end-to-end process, including supplier identification, "
    "sourcing, contracting, procurement against contracts, invoicing, "
    "payments, and spend analytics to ensure compliance and efficiency."
)

PARTICIPANT_KEYS = {"id", "program_id", "ref", "kind", "status",
                    "created_by", "created_utc"}


def load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def load_raw_descriptions():
    raw = json.load(open(os.path.join(_ROOT, "raw", "data_dump.json")))
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") in UNIT_ORDER and "service_desc" in o:
                found[o["id"]] = o["service_desc"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(raw)
    return found


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1/§2 — membership, claim table, verbatim evidence."""

    def setUp(self):
        self.specs = load_specs()
        self.by_id = {s["fork_id"]: s for s in self.specs}

    def test_sheet_count_order_and_membership(self):
        """6 sheets: 2 originals in order, then the unit's 4 in unit order."""
        self.assertEqual([s["fork_id"] for s in self.specs],
                         ORIGINALS + UNIT_ORDER)
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        unit = next(u for u in remainder["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        for fid in UNIT_ORDER:
            sheet = self.by_id[fid]
            self.assertEqual(sheet["deadramp_category"], "Finance")
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")

    def test_claim_table_pinned(self):
        """The literal per-fork claim table, originals and additions."""
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 9)  # 8 original + 1 addition claim

    def test_evidence_verbatim_and_descriptions_match_cache(self):
        """Every claim's evidence is a verbatim substring of its sheet's
        description, and each addition description equals the cached
        marketplace description exactly."""
        raw = load_raw_descriptions()
        self.assertEqual(set(raw), set(UNIT_ORDER))
        for fid in UNIT_ORDER:
            self.assertEqual(self.by_id[fid]["description"], raw[fid], fid)
        for sheet in self.specs:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              sheet["fork_id"])

    def test_census_citations_verbatim(self):
        """All 5 census citations for the unit verify as verbatim
        substrings of the forks' own descriptions (verification is
        recorded; it is not itself a claim)."""
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        checked = 0
        for fork in remainder["forks"]:
            if fork["fork_id"] in UNIT_ORDER:
                for citation in fork["citations"]:
                    self.assertIn(citation,
                                  self.by_id[fork["fork_id"]]["description"])
                    checked += 1
        self.assertEqual(checked, 5)

    def test_coupa_evidence_reanchored_to_functional_sentence(self):
        """Coupa's spend claim rests on the functional sentence (spend
        analytics), not the product-name title sentence — the
        name-only precedent recorded in ADDENDUM §2."""
        claims = self.by_id["F1308202329"]["functions_claimed"]
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["evidence"], COUPA_EVIDENCE)
        self.assertIn("spend analytics", claims[0]["evidence"])

    def test_near_miss_pins(self):
        """The zero-claim forks' near-misses, pinned as recorded:
        Innovest is "multi-currency", not "multi-tenant", and never
        says "SaaS offering"; Apptio is a "SaaS provider", not a
        "SaaS offering", and claims no "financial wellness";
        Momentum contains no \\bspend\\b token at all."""
        innovest = self.by_id["FR1821933307"]["description"]
        self.assertIn("multi-currency", innovest)
        self.assertNotIn("multi-tenant", innovest)
        self.assertNotIn("SaaS offering", innovest)
        apptio = self.by_id["F1603157879"]["description"]
        self.assertIn("SaaS provider", apptio)
        self.assertNotIn("SaaS offering", apptio)
        self.assertNotIn("financial wellness", apptio)
        momentum = self.by_id["FR2022243058"]["description"]
        self.assertIsNone(re.search(r"\bspend\b", momentum, re.IGNORECASE))
        self.assertIn("budget", momentum)  # substance present, family unclaimed
        coupa = self.by_id["F1308202329"]["description"]
        self.assertIsNone(re.search(r"\breporting\b", coupa, re.IGNORECASE))


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork against the unchanged
    Core (ADDENDUM §3): the records each fork's surface presupposes
    land in the Core forms that already exist."""

    def test_coupa_spend_claim_rides_core_budgets(self):
        """Coupa (spend_management, Core 5): a budget line plus a
        booking record compute spend-vs-budget from records."""
        store, audit, pid = H.make_store()
        traveler = H.make_traveler(store, pid, ref="coupa-trav")
        store.set_budget(pid, H.PERIOD,
                         [{"category": "air", "limit_cents": 50000}],
                         H.MEMBER)
        H.make_booking(store, pid, traveler["id"], kind="air",
                       amount_cents=30000)
        vs = store.spend_vs_budget(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(len(vs["lines"]), 1)
        line = vs["lines"][0]
        self.assertEqual(line["category"], "air")
        self.assertEqual(line["spent_cents"], 30000)
        self.assertEqual(line["variance_cents"], 20000)
        self.assertFalse(line["over_budget"])
        self.assertEqual(vs["total_spent_cents"], 30000)

    def test_apptio_allocation_records_are_budget_records(self):
        """Apptio (zero claims; cost-allocation substance): unbudgeted
        spend is computed and listed by category on read — the
        allocation record the substrate holds (Core 5)."""
        store, audit, pid = H.make_store()
        traveler = H.make_traveler(store, pid, ref="apptio-trav")
        store.set_budget(pid, H.PERIOD,
                         [{"category": "hotel", "limit_cents": 40000}],
                         H.MEMBER)
        H.make_booking(store, pid, traveler["id"], kind="air",
                       amount_cents=30000)
        vs = store.spend_vs_budget(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(vs["unbudgeted"],
                         [{"category": "air", "spent_cents": 30000}])
        self.assertEqual(vs["total_budgeted_cents"], 40000)
        self.assertEqual(vs["total_spent_cents"], 30000)

    def test_momentum_summary_computed_from_records(self):
        """Momentum (zero claims; federal financial substance): the
        per-period program summary (Core 7) is computed from wage
        records only — earned and disbursed totals exact."""
        store, audit, pid = H.make_store()
        employee = H.make_employee(store, pid, ref="momentum-emp")
        H.make_accrual(store, pid, employee["id"], earned_cents=100000)
        _req, dis = H.disbursed_request(store, pid, employee["id"],
                                        amount_cents=10000)
        summary = store.program_summary(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(summary["participants"], 1)
        self.assertEqual(summary["earned_cents"], 100000)
        self.assertEqual(summary["accessed_cents"], 10000)
        self.assertEqual(summary["disbursed_cents"], 10000)
        self.assertEqual(summary["pending_cents"], 0)
        self.assertEqual(dis["amount_cents"], 10000)

    def test_innovest_participant_shape_and_money_discipline(self):
        """Innovest (zero claims; trust-accounting surface): a
        participant record carries exactly the pinned opaque key set
        (no field can hold an account identifier), and non-integer
        amounts are rejected whole at the boundary (SI-10)."""
        store, audit, pid = H.make_store()
        employee = H.make_employee(store, pid, ref="innovest-emp")
        self.assertEqual(set(employee.keys()), PARTICIPANT_KEYS)
        with self.assertRaises(ValidationError):
            store.record_accrual(pid, employee["id"], H.PERIOD, 100.5,
                                 H.MEMBER)
        with self.assertRaises(ValidationError):
            store.record_accrual(pid, employee["id"], H.PERIOD, True,
                                 H.MEMBER)
        accrual = H.make_accrual(store, pid, employee["id"],
                                 earned_cents=50000)
        self.assertEqual(accrual["earned_cents"], 50000)

    def test_additions_earned_cap_still_enforced(self):
        """The group's signature invariant over addition-era records:
        two requests each within the earned amount whose sum exceeds
        it — the second is rejected whole, nothing stored, no id
        consumed (Core 3 / SI-10; this is the case the re-run cap
        drill trips from the additions module)."""
        store, audit, pid = H.make_store()
        employee = H.make_employee(store, pid, ref="cap-emp")
        H.make_accrual(store, pid, employee["id"], earned_cents=100000)
        first = H.make_request(store, pid, employee["id"],
                               amount_cents=60000)
        self.assertEqual(first["status"], "requested")
        with self.assertRaises(ValidationError):
            H.make_request(store, pid, employee["id"], amount_cents=40001,
                           date=H.DATE_JAN_2)
        requests = store.list_access_requests(pid, H.MEMBER)
        self.assertEqual([r["id"] for r in requests], [first["id"]])


if __name__ == "__main__":
    unittest.main()
