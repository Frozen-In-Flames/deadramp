"""Remainder addition (unit addition:grc-l3): spec integrity and
substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 44 (Governance, Risk, and
Compliance (GRC), CMMC L3-adjacent). The previously
uncategorized fork (Exiger Federal Cloud (EFC) - High) was
spec'd under the group's EXISTING 14-family taxonomy applied
verbatim — the additions extractor parses the TAXONOMY literal
out of the shipped ``scratch/extract.py`` via ``ast`` (parsed,
never executed, never re-typed), asserts taxonomy equality, and
reproduces the original fork's shipped claim table exactly
(2 claims, evidence included) before tagging the newcomer.

The newcomer claims **0 families** — a zero-claim fork. Its
entire marketplace description is one sentence (243 characters)
naming its own product and four of its own modules (Due
Diligence Intelligence, Third Party Management, Supply
Dynamics, Analytics); it contains no functional pattern phrase
of any of the 14 families, so the raw hit count is 0 across the
board and there is nothing for the wording-artifact corrections
to correct. The group total stays 2 claims (1 of 2 forks
claiming). The single census citation verifies verbatim — it is
the entire description — and tags nothing: verification is not
a claim, and census classification is not a claim either, in
either direction. The category's standing named absence at
this tier, ``policy_management``, survives: neither fork's
prose contains a policy token, so the family stands at 0 of 2
at L3-adjacent (its retirement at L2 by the Group 33 addition
does not carry up a tier on its own).

Neither claim nor absence extends the core: ``src/`` is
byte-identical. The substrate cases exercise the shipped core
as the newcomer would use it: a third-party-risk finding on a
governed system with its due-date status derived at read
(Core 5 — that assertion trips the group's signature
derivation drill by exactly one; see tests/README.md), an
evidence record verified by content with reviewer separation
(Core 4), an indicator result recorded verbatim (Core 3), and
a counts-only posture surface scanned recursively for any
score-like key (Core 7 — no score follows from anything in
this group). The fork's due-diligence, third-party-management,
and supply-chain engines are Extended (ADDENDUM section 5),
not implemented, and nothing in these cases claims them.
"""

import json
import os
import re
import unittest

from grc_helpers import ADMIN, MEMBER, fresh_store, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "FR2009746321",   # United Solutions — US AI
]
UNIT_ORDER = [
    "FR2122140784A",  # Covergent Solutions Inc dba Exiger
                      # Government Solutions (EGS) — Exiger
                      # Federal Cloud (EFC) - High
]

ALL_FAMILIES = [
    "evidence_management",
    "continuous_monitoring",
    "ksi_tracking",
    "vulnerability_remediation",
    "control_framework_compliance",
    "posture_reporting",
    "assessment_authorization",
    "risk_management",
    "policy_management",
    "audit_support",
    "platform_hosting",
    "identity_access_hooks",
    "workflow_automation",
    "api_integrations",
]

ORIGINAL_CLAIMS = {
    "FR2009746321": ["continuous_monitoring", "risk_management"],
}

# The literal claim table for the addition: zero claims.
EXPECTED_CLAIMS = {
    "FR2122140784A": [],
}

NEWCOMER_DESCRIPTION = (
    "Exiger Government Solutions (EGS) developed a "
    "Software-as-a-Service (SaaS) product named 1Exiger which "
    "provides access to multiple modules - Due Diligence "
    "Intelligence (DDIQ), Third Party Management (3PM), "
    "Supply Dynamics (SDX), and Analytics."
)


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description, census citation accounting,
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
                    if u["unit_id"] == "addition:grc-l3")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "grc-l3")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[1:]],
                         unit["fork_ids"])

    def test_original_claim_table_stands(self):
        """The original fork's shipped claim table stands
        exactly (2 claims: continuous_monitoring and
        risk_management, both from the Archangel passage, with
        the shipped evidence sentences)."""
        specs = _load_specs()
        sheet = _sheet(specs, "FR2009746321")
        got = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertEqual(got, ORIGINAL_CLAIMS["FR2009746321"])
        evidence = {c["function_id"]: c["evidence"]
                    for c in sheet["functions_claimed"]}
        self.assertEqual(
            evidence["continuous_monitoring"],
            "Additionally, CSPs and security professionals apply "
            "Blockchain, AI, and RPA to continuously monitor "
            "device logs and predict vulnerabilities and "
            "breaches.")
        self.assertEqual(
            evidence["risk_management"],
            "Lastly, security, supply chain, and risk management "
            "professionals apply AI to predict global security "
            "and supply chain risks.")

    def test_literal_claim_table_zero_claims(self):
        """The addition fork claims exactly nothing: its
        functions_claimed list is empty — the pinned zero-claim
        table, not a missing one."""
        sheet = _sheet(_load_specs(), "FR2122140784A")
        self.assertEqual(
            [c["function_id"] for c in sheet["functions_claimed"]],
            EXPECTED_CLAIMS["FR2122140784A"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_zero_claim_family_set_is_the_whole_taxonomy(self):
        """The newcomer's zero-claim set is all 14 families of
        the group's taxonomy."""
        sheet = _sheet(_load_specs(), "FR2122140784A")
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_group_totals(self):
        """The group total stays 2 claims; 1 of 2 forks claims.
        Family counts: continuous_monitoring 1, risk_management
        1 (of 2 forks each); the other 12 families stand at 0."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 2)
        zero = [s["fork_id"] for s in specs
                if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR2122140784A"])
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(
                    c["function_id"], []).append(s["fork_id"])
        self.assertEqual(by_family["continuous_monitoring"],
                         ["FR2009746321"])
        self.assertEqual(by_family["risk_management"],
                         ["FR2009746321"])
        self.assertEqual(len(by_family), 2)

    def test_addition_tier_fields(self):
        """The addition is FedRAMP High / Certified /
        L3-adjacent / SaaS / Public Cloud, so the High baseline
        is unchanged. Its source record carries no business
        categories (uncategorized in the source); the DeadRamp
        category is the census proposal, Governance, Risk, and
        Compliance (GRC)."""
        sheet = _sheet(_load_specs(), "FR2122140784A")
        self.assertEqual(
            sheet["vendor"],
            "Covergent Solutions Inc dba Exiger Government "
            "Solutions (EGS)")
        self.assertEqual(sheet["product"],
                         "Exiger Federal Cloud (EFC) - High")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Governance, Risk, and Compliance (GRC)")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description, verbatim — and it is
        exactly one sentence of 243 characters."""
        sheet = _sheet(_load_specs(), "FR2122140784A")
        self.assertEqual(sheet["description"],
                         _raw_product("FR2122140784A")["service_desc"])
        self.assertEqual(sheet["description"], NEWCOMER_DESCRIPTION)
        self.assertEqual(len(sheet["description"]), 243)

    def test_census_citation_verifies_and_tags_nothing(self):
        """Citation accounting: the fork's single census
        citation verifies as a strict verbatim substring — it
        is the entire description — and the census classified
        by substance ("due diligence and third-party management
        are the named risk functions"). The claim pass reads
        the same text for functional pattern phrases and finds
        none. Verification is not a claim, and classification
        is not a claim either, in either direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        cites = census["FR2122140784A"]["citations"]
        self.assertEqual(len(cites), 1)
        sheet = _sheet(_load_specs(), "FR2122140784A")
        self.assertIn(cites[0], sheet["description"])
        self.assertEqual(cites[0], sheet["description"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the fork's source record
        carries no certified-services block and no
        scope-exclusion segment. Its module list (DDIQ, 3PM,
        SDX, Analytics) enumerates the fork's OWN product
        modules — an in-scope enumeration of its own
        components, not a catalogue of third-party hosted
        applications. Matched text is the full text; the raw
        hit count is zero, so nothing was removed."""
        self.assertEqual(
            _raw_product("FR2122140784A")["certified_services"], [])
        desc = _sheet(_load_specs(), "FR2122140784A")["description"]
        self.assertNotIn("not authorized", desc.lower())

    def test_policy_management_absence_survives_at_this_tier(self):
        """Named-absence accounting: policy_management, the
        union spec's named absence at this tier, survives the
        addition — no sheet at L3-adjacent claims it, and the
        newcomer's prose contains no policy token at all. Its
        retirement at L2 (Group 33 addition) does not carry up
        a tier on its own."""
        specs = _load_specs()
        for s in specs:
            for c in s["functions_claimed"]:
                self.assertNotEqual(c["function_id"],
                                    "policy_management")
        desc = _sheet(specs, "FR2122140784A")["description"]
        self.assertIsNone(re.search(r"polic", desc, re.IGNORECASE))

    def test_near_miss_pins_exiger(self):
        """Exiger: the risk-adjacent substance is present in
        its own words as module names; the families' operative
        pattern phrases are absent, so every family stays at
        its shipped count for this fork."""
        desc = _sheet(_load_specs(), "FR2122140784A")["description"]
        low = desc.lower()
        # Substance present (module names — gaps, ADDENDUM
        # sections 2 and 5):
        self.assertIn("due diligence intelligence", low)
        self.assertIn("third party management", low)
        self.assertIn("supply dynamics", low)
        self.assertIn("analytics", low)
        self.assertIn("provides access to multiple modules", low)
        self.assertIn("software-as-a-service (saas)", low)
        # Family tokens absent:
        self.assertNotIn("risk management", low)
        self.assertNotIn("risk assessment", low)
        self.assertNotIn("risk register", low)
        self.assertNotIn("risk tracking", low)
        self.assertNotIn("risk", low)
        self.assertNotIn("third-party risk", low)
        self.assertNotIn("supply chain risk", low)
        self.assertIsNone(re.search(r"polic", low))
        self.assertNotIn("platform as a service", low)
        self.assertNotIn("paas", low)
        self.assertNotIn("role-based access control", low)
        self.assertNotIn("identity and access controls", low)
        self.assertIsNone(re.search(r"\bapis\b", low))
        self.assertIsNone(re.search(r"\bintegrations?\b", low))
        self.assertNotIn("continuously monitor", low)
        self.assertNotIn("continuous monitoring", low)
        self.assertNotIn("evidence", low)
        self.assertNotIn("audit", low)
        self.assertNotIn("assessor", low)
        self.assertNotIn("authority to operate", low)
        self.assertNotIn("vulnerabilit", low)
        self.assertNotIn("remediation", low)
        self.assertNotIn("workflow", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_exiger_third_party_finding_derivation(self):
        """Exiger shape: a third-party-risk finding (the record
        form a due-diligence / third-party-management finding
        lands in, Core 5) is opened on a governed system with
        severity recorded verbatim, moved in progress, and its
        due-date status is derived at read — current on the
        due date, overdue after it — while the stored record
        carries no derived status. The overdue assertion trips
        the group's signature derivation drill by exactly one.
        No score is computed: the finding carries no score,
        rating, or band key, and the counts-only posture
        surface scanned recursively contains no score-like key
        (Core 7)."""
        store, _system, _indicator = make_store()
        finding = store.create_finding(
            "Third-party vendor due-diligence finding",
            "SYS-001", "High", "assessment", "2026-06-30",
            actor=MEMBER)
        self.assertEqual(finding["severity"], "High")
        self.assertNotIn("derived_status", finding)
        for key in finding:
            self.assertNotIn("score", key.lower())
            self.assertNotIn("rating", key.lower())
            self.assertNotIn("band", key.lower())
        store.transition_finding(finding["id"], "in_progress",
                                 actor=MEMBER)
        on_due = store.get_finding(finding["id"], MEMBER,
                                   as_of="2026-06-30")
        self.assertEqual(on_due["derived_status"], "in_progress")
        past_due = store.get_finding(finding["id"], MEMBER,
                                     as_of="2026-07-01")
        self.assertEqual(past_due["derived_status"], "overdue")
        plain = store.get_finding(finding["id"], MEMBER)
        self.assertNotIn("derived_status", plain)

        def _scan(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    for bad in ("score", "rating", "grade",
                                "percent"):
                        self.assertNotIn(bad, k.lower())
                    _scan(v)
            elif isinstance(obj, list):
                for v in obj:
                    _scan(v)

        _scan(store.posture_summary(actor=ADMIN))

    def test_exiger_evidence_and_indicator_records(self):
        """Exiger shape: a due-diligence evidence artifact for
        the governed system is registered as a metadata record
        plus SHA-256 (Core 4), verifies by content (original
        True, tampered False), and is reviewed by an admin —
        the filing member may not review their own evidence —
        with the validation status recorded verbatim. An
        indicator result over the same system is recorded
        verbatim (Core 3): recording is Core; the fork's
        analytics engine that would produce such results
        automatically is Extended."""
        store, _system, _indicator = make_store()
        content = "third-party due-diligence dossier, Q3"
        ev = store.create_evidence(
            "3PM due-diligence dossier", content, ["RA-3"],
            ["SYS-001"], actor=MEMBER)
        self.assertEqual(ev["validation_status"], "unvalidated")
        self.assertTrue(
            store.verify_evidence(ev["id"], content, actor=MEMBER))
        self.assertFalse(store.verify_evidence(
            ev["id"], content + " (edited)", actor=MEMBER))
        with self.assertRaises(Exception):
            store.review_evidence(ev["id"], "Validated", actor=MEMBER)
        reviewed = store.review_evidence(
            ev["id"], "Validated", actor=ADMIN)
        self.assertEqual(reviewed["validation_status"], "Validated")
        result = store.record_indicator_result(
            "KSI-1", "SYS-001", "Reported by 3PM review",
            actor=MEMBER, timestamp="2026-06-15T12:00:00Z")
        self.assertEqual(result["status"], "Reported by 3PM review")


if __name__ == "__main__":
    unittest.main()
