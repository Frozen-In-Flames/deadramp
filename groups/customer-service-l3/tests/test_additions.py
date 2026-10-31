"""Remainder addition (unit addition:customer-service-l3): spec
integrity and substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for the Group 41 singleton (Customer
Service, L3-adjacent). The previously uncategorized fork
(Medallia GovCloud) was spec'd under the group's EXISTING
16-family taxonomy applied verbatim — the additions extractor
parses the TAXONOMY literal out of the shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed) and reproduces the original fork's shipped claim table
exactly before tagging the newcomer — including the original's
scoping fact: FedHIVE's own prose produces zero raw hits, and its
full text produces exactly the 6 third-party-catalogue families
recorded in ``scratch/function_counts.json``, every one excluded.

The newcomer claims **2 families**, both substantive:
``satisfaction_surveys`` (its own words: it captures experience
signals via "traditional surveys") and ``ai_assistance`` ("Medallia
applies proprietary AI technology"). The first claim retires the
category's standing named absence for satisfaction / CSAT surveys
at this tier; the second gives the already-registered AI
assistance gap a claimant at this tier. Neither claim extends the
core: surveys were a named absence (never built), AI assistance is
Extended (models), and the 10 core functions remain **carried, not
claimed** for both forks. The census twist is pinned, not hidden:
of the fork's 2 census citations, one tags no family and the
other is the satisfaction-surveys evidence sentence itself —
verification is not a claim, in either direction.

The substrate cases exercise the carried substrate the fork's
described surface presupposes: an experience/feedback signal
becomes a case record (Core 1) with an alert record linked to it
(Core 5), a public status update (Core 7), and breach derived at
read (Core 4); and the audit trail over that flow verifies as a
hash chain and localizes tampering (Core 10, AU-9). The survey
collection and AI insight engines themselves are Extended
(ADDENDUM section 5), not implemented, and nothing in these cases
claims them. The breach case trips the group's signature
``_is_breached`` drill and the audit case trips the hash-chain
drill, each by exactly one (see tests/README.md).
"""

import json
import os
import re
import unittest

from custsvc_helpers import AGENT, NOW, PAST_DUE, make_case, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "FR1802451335",  # Human Resources Technologies, Inc. (HRTec) — FedHIVE
]
UNIT_ORDER = [
    "FR1711262842",  # Medallia, Inc. — Medallia GovCloud
]

# The literal claim table for the addition, in taxonomy order.
EXPECTED_CLAIMS = {
    "FR1711262842": ["satisfaction_surveys", "ai_assistance"],
}

EXPECTED_EVIDENCE = {
    "satisfaction_surveys": (
        "Medallia captures experience signals created on daily "
        "journeys in-person, traditional surveys, on calls, digital "
        "channels, over video and social media, and IoT interactions."
    ),
    "ai_assistance": (
        "Once net new data is captured or by leveraging legacy data "
        "previously collected by customers, Medallia applies "
        "proprietary AI technology on data that is structured and "
        "unstructured (text and comments) to reveal personalized "
        "and predictive insights that can drive action towards "
        "positive business / organizational results and outcomes."
    ),
}


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
    table, verbatim description and evidence, census citations,
    near-miss pins, absence accounting."""

    def test_sheet_count_and_order(self):
        """2 sheets: the shipped original untouched in place, then
        the addition in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork,
        extending exactly this group."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:customer-service-l3")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "customer-service-l3")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[1:]],
                         unit["fork_ids"])

    def test_original_sheet_still_zero_claims(self):
        """The original fork's shipped table stands: FedHIVE
        claims zero families (its own prose is hosting-boundary
        prose; the 6 full-text families all sit in the excluded
        third-party catalogue)."""
        specs = _load_specs()
        self.assertEqual(
            _sheet(specs, "FR1802451335")["functions_claimed"], [])

    def test_literal_claim_table(self):
        """The addition fork claims exactly the 2 pinned families,
        in taxonomy order, with the pinned evidence sentences."""
        specs = _load_specs()
        sheet = _sheet(specs, "FR1711262842")
        got = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS["FR1711262842"])
        for claim in sheet["functions_claimed"]:
            self.assertEqual(claim["evidence"],
                             EXPECTED_EVIDENCE[claim["function_id"]])

    def test_group_totals(self):
        """The group total moves 0 -> 2 claims. Exactly 1 of the
        group's 2 forks — the original — still carries zero
        claims; the group's zero-claim era ends with the
        newcomer, pinned rather than smoothed over."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 2)
        zero = [s["fork_id"] for s in specs if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR1802451335"])

    def test_addition_tier_fields(self):
        """The addition is FedRAMP High / Certified /
        L3-adjacent / SaaS / Government Community Cloud, so the
        group stays single-tier and the High baseline is
        unchanged. Its source record carries no business
        categories (uncategorized in the source); the DeadRamp
        category is the census proposal, Customer Service."""
        sheet = _sheet(_load_specs(), "FR1711262842")
        self.assertEqual(sheet["vendor"], "Medallia, Inc.")
        self.assertEqual(sheet["product"], "Medallia GovCloud")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Customer Service")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description, verbatim (the group's
        original convention: stored raw, unstripped)."""
        sheet = _sheet(_load_specs(), "FR1711262842")
        self.assertEqual(sheet["description"],
                         _raw_product("FR1711262842")["service_desc"])

    def test_evidence_is_verbatim(self):
        """Every claim's evidence sentence appears verbatim in
        the fork's own description."""
        sheet = _sheet(_load_specs(), "FR1711262842")
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_verify(self):
        """Both census citations verify as verbatim substrings.
        The twist, pinned: citation 1 tags no family (it is not
        any claim's evidence), while citation 2 IS the
        satisfaction-surveys evidence sentence. Verification is
        not a claim, in either direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        cites = census["FR1711262842"]["citations"]
        self.assertEqual(len(cites), 2)
        sheet = _sheet(_load_specs(), "FR1711262842")
        for cite in cites:
            self.assertIn(cite, sheet["description"])
        evidences = [c["evidence"] for c in sheet["functions_claimed"]]
        self.assertNotIn(cites[0], evidences)
        self.assertEqual(cites[1], EXPECTED_EVIDENCE["satisfaction_surveys"])

    def test_no_exclusion_trap_for_newcomer(self):
        """The group's signature trap does not apply here: the
        fork's source record carries no certified-services block
        (the FedHIVE catalogue mechanism), and its description
        contains no hosted-application catalogue — the Salesforce
        / ServiceNow mention sits inside its own integration
        bullet. Nothing was excluded before matching."""
        self.assertEqual(
            _raw_product("FR1711262842")["certified_services"], [])
        desc = _sheet(_load_specs(), "FR1711262842")["description"]
        self.assertNotIn("enables the secure federal deployment", desc)

    def test_named_absence_accounting(self):
        """Satisfaction surveys retire as a named absence at this
        tier (claimed by the newcomer in its own words); the
        other standing named absence, knowledge base / help
        articles, survives — claimed by neither fork."""
        specs = _load_specs()
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(c["function_id"], []).append(s["fork_id"])
        self.assertEqual(by_family.get("satisfaction_surveys"),
                         ["FR1711262842"])
        self.assertNotIn("knowledge_base", by_family)

    def test_near_miss_pins_medallia(self):
        """Medallia: experience-management substance is present in
        its own words; the neighbouring family phrases are
        absent, so the near-miss families stay at 0."""
        desc = _sheet(_load_specs(), "FR1711262842")["description"]
        low = desc.lower()
        # Substance present (claims and gaps, ADDENDUM sections
        # 2 and 5):
        self.assertIn("traditional surveys", low)
        self.assertIn("proprietary ai technology", low)
        self.assertIn("service recovery", low)
        self.assertIn("analysis and alerts", low)
        self.assertIn("chat, phone, video, and contact centers", low)
        self.assertIn("fedramp high certified", low)
        self.assertIn("salesforce", low)
        self.assertIn("servicenow", low)
        # Family phrases absent:
        self.assertNotIn("ticket", low)
        self.assertIsNone(
            re.search(r"\bcases?\b|triag", desc, re.IGNORECASE))
        self.assertNotIn("live chat", low)
        self.assertNotIn("chat channel", low)
        self.assertNotIn("phone support", low)
        self.assertNotIn("telephony", low)
        self.assertNotIn("analytics", low)
        self.assertNotIn("dashboard", low)
        self.assertNotIn("nist 800-53", low)
        self.assertNotIn("authority to operate (ato)", low)
        self.assertNotIn("incident management", low)
        self.assertNotIn("automated detection", low)
        self.assertNotIn("knowledge base", low)
        self.assertNotIn("help article", low)
        self.assertNotIn("audit trail", low)
        self.assertNotIn("audit log", low)
        self.assertNotIn("role-based", low)
        self.assertNotIn("status updates", low)
        self.assertNotIn("status pages", low)
        self.assertNotIn("on-call", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_medallia_feedback_case_breach_flow(self):
        """Medallia: an experience signal ("service recovery", in
        its own words) becomes a Core 1 case record against an
        opaque requester reference (Core 2), assigned (Core 3);
        a real-time signal becomes a Core 5 alert record linked
        to the case and worked to resolved; a public update is
        posted (Core 7); and the past-due case reads breached,
        derived at read (Core 4 — this assertion trips the
        group's signature _is_breached drill). The survey that
        produced the signal and the AI that scored it are
        Extended — nothing here collects feedback or runs a
        model."""
        store, _audit, requester, rsp1, _rsp2 = make_store()
        case = make_case(
            store, requester,
            title="Survey follow-up: citizen trust concern",
            body="Experience signal flagged for service recovery.",
            channel="survey", due_at=PAST_DUE)
        store.assign_case(case["id"], rsp1["id"], AGENT)
        alert = store.ingest_alert(
            "exp-signal-042", "Negative experience signal spike",
            "major", AGENT, case_id=case["id"])
        store.acknowledge_alert(alert["id"], AGENT)
        resolved = store.resolve_alert(alert["id"], AGENT)
        self.assertEqual(resolved["state"], "resolved")
        upd = store.add_case_update(
            case["id"], "Service recovery outreach started.",
            AGENT, public=True)
        self.assertTrue(upd["public"])
        view = store.get_case(case["id"], AGENT, now=NOW)
        self.assertEqual(view["assignee"], rsp1["id"])
        self.assertTrue(view["breached"],
                        "an overdue open case must read breached=True")
        status = store.public_status(AGENT, now=NOW)
        self.assertEqual(status["breached_cases"], 1)
        linked = store.list_alerts(AGENT, case_id=case["id"])
        self.assertEqual([a["id"] for a in linked], [alert["id"]])

    def test_medallia_audit_chain_detects_tampering(self):
        """Medallia: the newcomer's flow writes into the Core 10
        append-only audit log; the chain verifies clean, and an
        in-place mutation of a stored entry is localized at
        exactly its index (AU-9 — this assertion trips the
        group's hash-chain drill)."""
        store, audit, requester, _rsp1, _rsp2 = make_store()
        make_case(store, requester,
                  title="Feedback signal case",
                  body="Opened from an experience signal.")
        self.assertEqual(audit.verify_chain(), (True, None))
        audit._entries[1]["actor"] = "mallory"
        self.assertEqual(audit.verify_chain(), (False, 1))


if __name__ == "__main__":
    unittest.main()
