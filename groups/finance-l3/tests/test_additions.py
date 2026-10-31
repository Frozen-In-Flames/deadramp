"""Remainder addition — Finance L3-adjacent (unit ``addition:finance-l3``).

Traces to: ADDENDUM.md §§1–3 — the 1 previously uncategorized fork
(OneStream Cloud - High) spec'd under the group's existing 8-family
taxonomy applied verbatim, joining the zero-claim founding fork
(AWS GovCloud), and the substrate cases the newcomer's surface
exercises against the unchanged Core.

Spec-integrity pins: sheet count / append order / membership
against ``remainder.json``; the literal per-fork claim table (the
founding fork's empty table exactly as shipped; the newcomer's
2 claims — ``reporting`` and ``hosting_platform``); verbatim
evidence; descriptions equal to the cached marketplace text; the
single census citation, which verifies verbatim AND is itself the
``reporting`` evidence sentence (verification coinciding with a
claim, recorded as such); and the near-miss pins recorded in
ADDENDUM §2 ("budgeting" is not the ``spend`` token; integration
prose is not the ``api_platform`` verbatim phrase; the category's
standing trading & investment execution absence stands — no
trading token of any kind).
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

UNIT_ID = "addition:finance-l3"
UNIT_ORDER = ["FR1721059275A"]
ORIGINALS = ["F1603047866"]

ALL_FAMILIES = ["earned_wage_access", "financial_wellness",
                "travel_booking", "travel_management",
                "spend_management", "reporting", "api_platform",
                "hosting_platform"]

EXPECTED_CLAIMS = {
    "F1603047866": [],
    "FR1721059275A": ["reporting", "hosting_platform"],
}

ZERO_CLAIM_FAMILIES = [f for f in ALL_FAMILIES
                       if f not in EXPECTED_CLAIMS["FR1721059275A"]]

REPORTING_EVIDENCE = (
    "OneStream is a Corporate Performance Management (CPM) platform "
    "designed to support financial consolidation, reporting, planning, "
    "budgeting, and forecasting."
)
HOSTING_EVIDENCE = (
    "Delivered as a SaaS offering, the OneStream Government Community "
    "Cloud is hosted via Microsoft Azure Government and tailored to meet "
    "the needs of federal, state, local, and tribal governments as well "
    "as research institutions and government contractors."
)
SECOND_REPORTING_SENTENCE = (
    "The platform also supports data integration from multiple ERP and "
    "financial systems, enabling streamlined financial reporting and "
    "analysis."
)


def load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def load_raw_descriptions(ids):
    raw = json.load(open(os.path.join(_ROOT, "raw", "data_dump.json")))
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") in ids and "service_desc" in o:
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
        """2 sheets: the founding fork, then the unit's 1 fork."""
        self.assertEqual([s["fork_id"] for s in self.specs],
                         ORIGINALS + UNIT_ORDER)
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        unit = next(u for u in remainder["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        sheet = self.by_id["FR1721059275A"]
        self.assertEqual(sheet["vendor"], "OneStream Software")
        self.assertEqual(sheet["product"], "OneStream Cloud - High")
        self.assertEqual(sheet["deadramp_category"], "Finance")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        # Uncategorized in the source; the census assignment to
        # Finance is what this sheet records (ADDENDUM §1).
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claim_table_pinned(self):
        """The literal per-fork claim table, founder and addition."""
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 2)  # founder 0 + newcomer 2
        claiming = [s["fork_id"] for s in self.specs
                    if s["functions_claimed"]]
        self.assertEqual(claiming, ["FR1721059275A"])  # 1 of 2 claiming
        counts = {}
        for s in self.specs:
            for c in s["functions_claimed"]:
                counts[c["function_id"]] = counts.get(c["function_id"], 0) + 1
        self.assertEqual(counts, {"reporting": 1, "hosting_platform": 1})
        for fam in ZERO_CLAIM_FAMILIES:
            self.assertNotIn(fam, counts)

    def test_evidence_verbatim_and_descriptions_match_cache(self):
        """Evidence strings are exact, and both descriptions equal the
        cached marketplace text."""
        raw = load_raw_descriptions(set(ORIGINALS + UNIT_ORDER))
        self.assertEqual(set(raw), set(ORIGINALS + UNIT_ORDER))
        for fid in ORIGINALS + UNIT_ORDER:
            self.assertEqual(self.by_id[fid]["description"], raw[fid], fid)
        claims = {c["function_id"]: c
                  for c in self.by_id["FR1721059275A"]["functions_claimed"]}
        self.assertEqual(claims["reporting"]["evidence"], REPORTING_EVIDENCE)
        self.assertEqual(claims["hosting_platform"]["evidence"],
                         HOSTING_EVIDENCE)
        for sheet in self.specs:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              sheet["fork_id"])

    def test_first_matching_sentence_is_the_evidence(self):
        """``reporting`` also fires on a later sentence; the booked
        evidence is the FIRST matching sentence (house rule)."""
        desc = self.by_id["FR1721059275A"]["description"]
        self.assertIn(SECOND_REPORTING_SENTENCE, desc)
        claims = {c["function_id"]: c
                  for c in self.by_id["FR1721059275A"]["functions_claimed"]}
        self.assertNotEqual(claims["reporting"]["evidence"],
                            SECOND_REPORTING_SENTENCE)
        self.assertLess(desc.index(REPORTING_EVIDENCE),
                        desc.index(SECOND_REPORTING_SENTENCE))

    def test_census_citation_verifies_and_is_the_reporting_evidence(self):
        """The unit's single census citation verifies verbatim — and,
        unusually, it IS the reporting evidence sentence: verification
        and claim coincide here, recorded rather than assumed
        (ADDENDUM §2)."""
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        fork = next(f for f in remainder["forks"]
                    if f["fork_id"] == "FR1721059275A")
        self.assertEqual(fork["build_unit"], UNIT_ID)
        self.assertEqual(fork["current_category"],
                         "Uncategorized (none in source)")
        self.assertEqual(len(fork["citations"]), 1)
        citation = fork["citations"][0]
        self.assertIn(citation, self.by_id["FR1721059275A"]["description"])
        self.assertEqual(citation, REPORTING_EVIDENCE)

    def test_near_miss_pins(self):
        """ADDENDUM §2 near-misses, pinned at the token level."""
        desc = self.by_id["FR1721059275A"]["description"]
        # "budgeting" is in the reporting evidence sentence itself,
        # but spend_management needs the spend token — absent.
        self.assertIn("budgeting", desc)
        self.assertIsNone(re.search(r"\bspend\b", desc, re.IGNORECASE))
        # Integration is asserted in substance (sentences 5–6), but
        # api_platform's verbatim phrase is absent — no claim.
        self.assertIn("integrates with Microsoft Office", desc)
        self.assertNotIn("open technology platform", desc)
        # The hosting claim rests on "SaaS offering" alone; the
        # family's other phrase is absent.
        self.assertIn("SaaS offering", desc)
        self.assertNotIn("multi-tenant", desc)
        # No earned-wage, wellness, or travel token of any kind.
        for token in ("earned wages", "financial wellness",
                      "booking", "travel"):
            self.assertNotIn(token, desc.lower())

    def test_named_absences_stand(self):
        """The category's named absences (UNION-SPEC) survive at this
        tier: no banking, payroll, lending/credit, trading, or tax
        token exists in the newcomer's description. In particular
        the standing absence — trading & investment execution —
        stands: "forecasting" is planning prose, not execution."""
        desc = self.by_id["FR1721059275A"]["description"].lower()
        for token in ("trad", "invest", "execut", "lend", "credit",
                      "payroll", "bank", "tax"):
            self.assertNotIn(token, desc, token)
        self.assertIn("forecasting", desc)


class TestOneStreamSubstrate(unittest.TestCase):
    """ADDENDUM §3 — the carried substrate exercised in the
    newcomer's shape: a finance program's period close, where the
    claimed ``reporting`` family's records form (Core 7 summaries
    computed on read, Core 5 spend-vs-budget) derives every number
    from records in integer cents. The newcomer claims no other
    Core family; these cases claim none on its behalf."""

    def setUp(self):
        self.store, self.audit, self.pid = H.make_store()
        self.p1 = self.store.create_participant(
            self.pid, "emp-001", "employee", H.MEMBER)
        self.p2 = self.store.create_participant(
            self.pid, "emp-002", "employee", H.MEMBER)
        self.p3 = self.store.create_participant(
            self.pid, "trv-001", "traveler", H.MEMBER)

    def test_period_close_reporting_from_records(self):
        """Consolidation-shaped close: accruals, one disbursed and
        one pending access, bookings, and a budget consolidate into
        the on-read summary and spend-vs-budget, to the cent."""
        store, pid = self.store, self.pid
        store.record_accrual(pid, self.p1["id"], H.PERIOD, 100000, H.MEMBER)
        store.record_accrual(pid, self.p2["id"], H.PERIOD, 50000, H.MEMBER)
        req1 = store.request_access(pid, self.p1["id"], H.PERIOD, 30000,
                                    H.DATE_JAN, H.MEMBER)
        store.decide_access(pid, req1["id"], True, H.ADMIN)
        store.record_disbursement(pid, req1["id"], H.DATE_JAN_2, H.MEMBER)
        store.request_access(pid, self.p2["id"], H.PERIOD, 10000,
                             H.DATE_JAN, H.MEMBER)  # left pending
        air = store.create_booking(pid, self.p3["id"], "air",
                                   "2026-01-10", "2026-01-12", 45000,
                                   H.MEMBER)
        store.confirm_booking(pid, air["id"], H.MEMBER)
        store.create_booking(pid, self.p3["id"], "hotel",
                             "2026-01-10", "2026-01-11", 20000, H.MEMBER)
        store.set_budget(pid, H.PERIOD, [
            {"category": "air", "limit_cents": 40000},
            {"category": "hotel", "limit_cents": 25000},
            {"category": "earned_wage", "limit_cents": 35000},
        ], H.MEMBER)

        vs = store.spend_vs_budget(pid, H.PERIOD, H.MEMBER)
        lines = {line["category"]: line for line in vs["lines"]}
        self.assertEqual(lines["air"]["spent_cents"], 45000)
        self.assertEqual(lines["air"]["variance_cents"], -5000)
        self.assertTrue(lines["air"]["over_budget"])
        self.assertEqual(lines["hotel"]["spent_cents"], 20000)
        self.assertEqual(lines["hotel"]["variance_cents"], 5000)
        self.assertFalse(lines["hotel"]["over_budget"])
        self.assertEqual(lines["earned_wage"]["spent_cents"], 30000)
        self.assertEqual(vs["total_budgeted_cents"], 100000)
        self.assertEqual(vs["total_spent_cents"], 95000)
        self.assertEqual(vs["total_variance_cents"], 5000)
        self.assertEqual(vs["unbudgeted"], [])

        summary = store.program_summary(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(summary["participants"], 3)
        self.assertEqual(summary["earned_cents"], 150000)
        self.assertEqual(summary["accessed_cents"], 30000)
        self.assertEqual(summary["disbursed_cents"], 30000)
        self.assertEqual(summary["pending_cents"], 10000)
        self.assertEqual(summary["bookings"]["air"],
                         {"count": 1, "total_cents": 45000})
        self.assertEqual(summary["bookings"]["hotel"],
                         {"count": 1, "total_cents": 20000})
        for key in ("earned_cents", "accessed_cents", "disbursed_cents",
                    "pending_cents"):
            self.assertIs(type(summary[key]), int, key)

    def test_float_and_bool_amounts_rejected_whole(self):
        """The integer-cents boundary in the newcomer's shape: a
        float or boolean amount is rejected and stores nothing."""
        store, pid = self.store, self.pid
        for bad in (100.5, 100.0, True):
            with self.assertRaises(ValidationError):
                store.record_accrual(pid, self.p1["id"], H.PERIOD, bad,
                                     H.MEMBER)
        self.assertEqual(store.list_accruals(pid, H.MEMBER), [])
        summary = store.program_summary(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(summary["earned_cents"], 0)

    def test_over_cap_request_rejected_whole(self):
        """The earned-cap invariant in the newcomer's shape: a
        request one cent over the period's earned amount is
        rejected, stores nothing, and consumes no id. (This is the
        additions case the Drill 1 mutant trips — tests/README.md.)
        """
        store, pid = self.store, self.pid
        store.record_accrual(pid, self.p1["id"], H.PERIOD, 20000, H.MEMBER)
        with self.assertRaises(ValidationError):
            store.request_access(pid, self.p1["id"], H.PERIOD, 20001,
                                 H.DATE_JAN, H.MEMBER)
        self.assertEqual(store.list_access_requests(pid, H.MEMBER), [])
        summary = store.program_summary(pid, H.PERIOD, H.MEMBER)
        self.assertEqual(summary["pending_cents"], 0)


if __name__ == "__main__":
    unittest.main()
