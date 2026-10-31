"""Remainder additions — unit addition:customer-service-l1 (1 fork).

Traces to: the addendum for Zendesk / Zendesk Customer Support and
Help Desk Platform (FR1821856903), appended to the shipped Customer
Service L1 group under its existing 16-family taxonomy applied
verbatim. The newcomer is a ZERO-CLAIM fork: its three-sentence
marketplace description contains no taxonomy token at all, so its
sheet claims nothing and the pins below are pins on an absence —
sheet count and append order, unit membership against
../../remainder.json, the literal (empty) claim table, the originals'
claim tables reproduced exactly, the census citations (verified as
text; both tag nothing), the near-miss pins, and the group's updated
totals. Two substrate cases exercise the shipped Core in the shape
the fork's described function presupposes — a help-desk case flow
with a public status update (the records substrate, carried not
claimed), and a breach-derivation case that trips under the group's
signature _is_breached mutant.
"""

import json
import os
import unittest

from custsvc_helpers import (AGENT, NOW, PAST_DUE, make_case, make_store)

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR1821856903"
ORIGINAL_IDS = ["FR2310974411", "FR2604835605"]
ALL_FAMILIES = [
    "case_ticket_management", "event_detection_response",
    "alert_prioritization", "automation_workflows", "oncall_scheduling",
    "responder_assignment", "status_communication",
    "governance_risk_compliance", "compliance_frameworks",
    "knowledge_base", "satisfaction_surveys", "realtime_channels",
    "ai_assistance", "reporting_dashboards", "access_control",
    "audit_logging",
]
PAGERDUTY_CLAIMS = [
    "case_ticket_management", "event_detection_response",
    "alert_prioritization", "automation_workflows", "oncall_scheduling",
    "responder_assignment", "status_communication",
]
RISKUITY_CLAIMS = ["governance_risk_compliance"]


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(fork_id):
    for row in _load_specs():
        if row["fork_id"] == fork_id:
            return row
    raise AssertionError("sheet missing: %s" % fork_id)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """Addendum sections 1/2: membership, order, the empty claim table."""

    def test_sheet_count_and_append_order(self):
        """3 sheets: the original 2 in shipped order, newcomer last."""
        ids = [r["fork_id"] for r in _load_specs()]
        self.assertEqual(ids, ORIGINAL_IDS + [FORK_ID])

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork list."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:customer-service-l1"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertIn(FORK_ID, [r["fork_id"] for r in _load_specs()])

    def test_literal_claim_table_newcomer_is_empty(self):
        """The newcomer claims exactly nothing under the verbatim taxonomy."""
        self.assertEqual(_sheet(FORK_ID)["functions_claimed"], [])

    def test_original_claim_tables_unchanged(self):
        """The originals' shipped claim tables stand exactly as shipped
        (the extractor's reproduction proof, pinned): PagerDuty 7,
        Riskuity 1 (its compliance_frameworks raw hit stays removed)."""
        pd_claims = [c["function_id"]
                     for c in _sheet("FR2310974411")["functions_claimed"]]
        rk_claims = [c["function_id"]
                     for c in _sheet("FR2604835605")["functions_claimed"]]
        self.assertEqual(pd_claims, PAGERDUTY_CLAIMS)
        self.assertEqual(rk_claims, RISKUITY_CLAIMS)

    def test_zero_claim_set_is_the_whole_taxonomy(self):
        """Every one of the 16 families is unclaimed by the newcomer."""
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        self.assertEqual(claimed, set())
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_registry_fields_as_published(self):
        """Sheet fields record the source as published: LI-SaaS at L1,
        Certified, SaaS / Public Cloud, empty business categories;
        forks.json files the fork as uncategorized and the census
        assignment recorded in deadramp_category is Customer Service."""
        sheet = _sheet(FORK_ID)
        self.assertEqual(sheet["vendor"], "Zendesk")
        self.assertEqual(sheet["product"],
                         "Zendesk Customer Support and Help Desk Platform")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Customer Service")

    def test_census_citations_verify_but_tag_nothing(self):
        """Both census citations are verbatim description text — they
        are the description's first two sentences — and neither is a
        claim's evidence, because there are no claims (verification
        is not a claim)."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "class_all.json")) as fh:
            cls = json.load(fh)
        entry = [r for r in cls if r.get("fork_id") == FORK_ID]
        self.assertEqual(len(entry), 1)
        citations = entry[0]["citations"]
        self.assertEqual(len(citations), 2)
        sheet = _sheet(FORK_ID)
        for cit in citations:
            self.assertIn(cit, sheet["description"])
        self.assertTrue(sheet["description"].startswith(citations[0]))

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the text yet tag no
        family: 'self-service' without 'article' (knowledge_base),
        'customer service platform' with no ticket/case token
        (case_ticket_management), 'great support' with no 'phone
        support'/channel token (realtime_channels)."""
        desc = _sheet(FORK_ID)["description"]
        self.assertIn("self-service", desc)
        self.assertNotIn("self-service article", desc)
        self.assertIn("customer service platform", desc)
        self.assertIn("provide great support", desc)
        self.assertNotIn("phone support", desc)
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        for fam in ("knowledge_base", "case_ticket_management",
                    "realtime_channels", "satisfaction_surveys"):
            self.assertNotIn(fam, claimed)

    def test_group_totals(self):
        """Updated union: 3 forks, 8 claims (unchanged), 2 of 3
        claiming, exactly 1 zero-claim fork; the case/ticket family
        is still claimed by exactly 1 of 3."""
        rows = _load_specs()
        total = sum(len(r["functions_claimed"]) for r in rows)
        claiming = sum(1 for r in rows if r["functions_claimed"])
        zero = [r["fork_id"] for r in rows if not r["functions_claimed"]]
        self.assertEqual(total, 8)
        self.assertEqual(claiming, 2)
        self.assertEqual(zero, [FORK_ID])
        ct = sum(1 for r in rows for c in r["functions_claimed"]
                 if c["function_id"] == "case_ticket_management")
        self.assertEqual(ct, 1)


class TestZendeskSubstrate(unittest.TestCase):
    """The described function's shape on the shipped Core. The fork
    claims no family, so these cases exercise the records substrate
    its help-desk function presupposes — carried, not claimed."""

    def setUp(self):
        self.store, self.audit, self.requester, self.rsp1, _ = make_store()

    def test_helpdesk_case_flow_with_public_status(self):
        """A support case from an opaque-ref requester: assigned,
        opened, a public update surfaces in the derived public
        status view while an internal note never does, and resolving
        the case returns the view to operational."""
        case = make_case(self.store, self.requester,
                         title="Password reset loop",
                         body="Requester cannot complete a reset.")
        case = self.store.assign_case(case["id"], self.rsp1["id"], AGENT)
        self.assertEqual(case["assignee"], self.rsp1["id"])
        self.store.set_case_status(case["id"], "open", AGENT)
        self.store.add_case_update(case["id"], "internal triage note",
                                   AGENT, public=False)
        self.store.add_case_update(case["id"], "We are working on it",
                                   AGENT, public=True)
        view = self.store.public_status(AGENT, now=NOW)
        bodies = [u["body"] for u in view["public_updates"]]
        self.assertEqual(bodies, ["We are working on it"])
        self.store.set_case_status(case["id"], "in_progress", AGENT)
        self.store.set_case_status(case["id"], "resolved", AGENT)
        self.assertEqual(
            self.store.public_status(AGENT, now=NOW)["overall"],
            "operational")

    def test_due_case_breach_derivation(self):
        """A past-due open support case reads breached, counts in the
        registry report, and degrades the public status view — all
        derived at read (trips under the _is_breached mutant; see
        tests/README.md drill record)."""
        case = make_case(self.store, self.requester, due_at=PAST_DUE)
        view = self.store.get_case(case["id"], AGENT, now=NOW)
        self.assertTrue(view["breached"])
        rep = self.store.report_summary(AGENT, now=NOW)
        self.assertEqual(rep["breached_cases"], 1)
        status = self.store.public_status(AGENT, now=NOW)
        self.assertEqual(status["breached_cases"], 1)
        self.assertEqual(status["overall"], "degraded")


if __name__ == "__main__":
    unittest.main()
