"""Remainder additions — unit addition:ai-l2 (1 fork).

Traces to: ADDENDUM.md (the addendum to UNION-SPEC.md for the
remainder census addition). The newcomer is FR2214346691 —
Secunetics, Inc. / Gobo Framework (Gobo), FedRAMP Moderate,
previously uncategorized, classified Artificial Intelligence (AI)
by the remainder census from its own description.

Two halves:

- Spec integrity: the appended sheet is pinned literally — the
  claim table under the group's existing 16-family taxonomy applied
  verbatim, the zero-claim family set, verbatim evidence, the
  census citation, and the near-miss pins (family-adjacent phrases
  that are present in the description yet tag no family).
- Substrate: the fork's claimed surface exercised against the
  shipped core in the fork's own shape — a cognitive-automation
  invocation through the gateway (whose responder is a labeled
  reference stub, never a learned model: the agentic family's
  platform side) under a human-in-the-loop policy rule, with the
  audit trail recording both the completion and the block (the
  audit family's Core side).
"""

import json
import os
import unittest

from aigateway_helpers import ADMIN, MEMBER, make_store
from aigateway.errors import PolicyBlocked
from aigateway.store import REFERENCE_NOTICE

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

FORK_ID = "FR2214346691"

EXPECTED_CLAIMS = {
    "agentic_workflows": (
        "Gobo provides an intuitive, AI-enabled cognitive automation "
        "platform designed to analyze complex datasets, apply "
        "intelligent operational logic, and streamline workflows "
        "across enterprise IT infrastructure, services, and business "
        "processes."
    ),
    "audit_logging": (
        "Through secure, web-based applications called I2Apps, Gobo "
        "automates routine engineering and operations tasks while "
        "maintaining strict human-in-the-loop control, auditability, "
        "and governance."
    ),
}

ALL_FAMILIES = {
    "learned_inference", "model_gateway", "model_governance",
    "usage_metering", "audit_logging", "access_control",
    "multi_tenancy", "guardrails", "interaction_records",
    "zero_persistence", "evaluation_records", "api_integration",
    "agentic_workflows", "document_automation",
    "analytics_reporting", "contact_center",
}

CENSUS_CITATION = (
    "Gobo provides an intuitive, AI-enabled cognitive automation "
    "platform designed to analyze complex datasets, apply "
    "intelligent operational logic, and streamline workflows across "
    "enterprise IT infrastructure, services, and business processes."
)

# Phrases present in the description that tag NO family — the
# near-miss pins. Each entry: (phrase in description, family it
# does not claim).
NEAR_MISSES = [
    ("AI-enabled", "learned_inference"),          # not "ai-powered"
    ("intelligent agents", "learned_inference"),  # not "ai agents"
    ("semantic intelligence", "learned_inference"),
    ("public comment analysis", "analytics_reporting"),  # analysis != analytics
    ("integrates seamlessly", "api_integration"),  # no API token
    ("governance", "model_governance"),           # not "model governance"
    ("quality of outcomes", "evaluation_records"),  # not "quality management"
    ("Invoice Management", "document_automation"),  # not "invoice processing"
    ("Invoice Management", "usage_metering"),     # no "billing"
    ("vendor-agnostic", "multi_tenancy"),         # not multi-tenant
    ("human-in-the-loop control", "guardrails"),  # no guardrail token
    ("human-in-the-loop control", "access_control"),
]


def _load_specs():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1/§2: membership, the literal claim table, verbatim
    evidence, census citation, near-miss pins, group totals."""

    def setUp(self):
        self.specs = _load_specs()
        self.sheet = self.specs[-1]

    def test_sheet_appended_with_unit_membership(self):
        """The unit's one fork is appended as sheet 12; the original
        11 sheets keep their order and fork set."""
        self.assertEqual(len(self.specs), 12)
        self.assertEqual(self.sheet["fork_id"], FORK_ID)
        self.assertEqual(self.sheet["vendor"], "Secunetics, Inc.")
        self.assertEqual(self.sheet["product"], "Gobo Framework (Gobo)")
        self.assertEqual(self.sheet["service_model"], ["SaaS"])
        self.assertEqual(self.sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(self.sheet["cmmc_tier"], "L2")
        self.assertEqual(self.sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(self.sheet["deadramp_category"],
                         "Artificial Intelligence (AI)")
        original_ids = {s["fork_id"] for s in self.specs[:11]}
        self.assertEqual(len(original_ids), 11)
        self.assertNotIn(FORK_ID, original_ids)

    def test_membership_matches_remainder_unit(self):
        """remainder.json's addition:ai-l2 unit names exactly this
        fork, and it extends this group."""
        with open(_REMAINDER_PATH) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:ai-l2"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertEqual(unit[0]["extends_group"], "ai-l2")

    def test_literal_claim_table(self):
        """Exactly 2 claims: agentic_workflows and audit_logging,
        with the pinned evidence sentences."""
        claims = {c["function_id"]: c["evidence"]
                  for c in self.sheet["functions_claimed"]}
        self.assertEqual(claims, EXPECTED_CLAIMS)

    def test_zero_claim_families(self):
        """The other 14 taxonomy families are claimed by no one in
        this sheet — pinned as a set, not left implicit."""
        claimed = {c["function_id"] for c in self.sheet["functions_claimed"]}
        self.assertEqual(ALL_FAMILIES - claimed,
                         ALL_FAMILIES - set(EXPECTED_CLAIMS))

    def test_evidence_is_verbatim_description_text(self):
        """Every claim's evidence is a verbatim substring of the
        fork's own stored description."""
        for c in self.sheet["functions_claimed"]:
            self.assertIn(c["evidence"], self.sheet["description"])

    def test_census_citation_verifies(self):
        """The census's starting citation for this fork verifies as
        verbatim description text (verification is not itself a
        claim: it is the agentic evidence sentence, and it tags
        exactly that one family)."""
        self.assertIn(CENSUS_CITATION, self.sheet["description"])
        self.assertEqual(EXPECTED_CLAIMS["agentic_workflows"],
                         CENSUS_CITATION)

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the description
        yet tag no family — the taxonomy was applied verbatim, not
        re-tuned for the newcomer."""
        claimed = {c["function_id"] for c in self.sheet["functions_claimed"]}
        for phrase, family in NEAR_MISSES:
            self.assertIn(phrase, self.sheet["description"],
                          f"pin premise gone: {phrase!r} not in description")
            self.assertNotIn(family, claimed,
                             f"{family} claimed via near-miss {phrase!r}")

    def test_agents_sentence_tags_nothing(self):
        """The fork's most agentic sentence — 'intelligent agents to
        orchestrate complex administrative and technical processes'
        — contains neither 'ai agents' nor an automat* token, so it
        is evidence for no claim; the agentic claim rests on the
        description's automation wording elsewhere."""
        desc = self.sheet["description"]
        self.assertIn("intelligent agents to orchestrate", desc)
        for c in self.sheet["functions_claimed"]:
            self.assertNotIn("intelligent agents", c["evidence"])

    def test_group_totals(self):
        """Combined group: 12 forks, 47 claims, 12 of 12 claiming;
        agentic and audit families each gain exactly one claimant;
        learned inference is unchanged at 8."""
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in self.specs), 47)
        self.assertTrue(all(s["functions_claimed"] for s in self.specs))
        counts = {}
        for s in self.specs:
            for c in s["functions_claimed"]:
                counts[c["function_id"]] = counts.get(c["function_id"], 0) + 1
        self.assertEqual(counts["agentic_workflows"], 5)
        self.assertEqual(counts["audit_logging"], 5)
        self.assertEqual(counts["learned_inference"], 8)


class TestAdditionSubstrate(unittest.TestCase):
    """ADDENDUM §3: the fork's shape run against the shipped core —
    a cognitive-automation invocation (rules responder, labeled
    stub) under a human-in-the-loop policy rule, audited both ways.
    """

    def _automation_store(self):
        store, audit, _model = make_store()
        store.register_model(
            "cognitive-automation", "rules", ADMIN,
            provider="reference",
            capabilities=["automation"],
            config={
                "rules": [{
                    "match": "invoice",
                    "response": "Reconciliation queued for human review",
                }],
                "default": "Task queued for human review",
            })
        return store, audit

    def test_automation_invocation_is_a_labeled_stub_and_audited(self):
        """An EIS-flavored automation prompt completes through the
        gateway; the output is the configured rule's response,
        labeled reference_stub with the pinned notice (no learned
        model is claimed for the fork's automation surface), and
        the invocation is metered and audited."""
        store, audit = self._automation_store()
        rec = store.invoke(
            "cognitive-automation",
            "automate invoice reconciliation for this CLIN",
            MEMBER)
        self.assertEqual(rec["status"], "completed")
        self.assertEqual(rec["output"],
                         "Reconciliation queued for human review")
        self.assertIs(rec["reference_stub"], True)
        self.assertEqual(rec["notice"], REFERENCE_NOTICE)
        self.assertGreater(rec["usage"]["total_tokens"], 0)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("model_register", actions)
        self.assertIn("invoke", actions)

    def test_human_in_the_loop_block_is_recorded_and_audited(self):
        """The fork's 'strict human-in-the-loop control' surface,
        as the build can hold it: a policy rule blocks an
        unreviewed automation prompt, stores exactly one
        blocked_input record, completes nothing, and the block is
        in the audit trail (the audit_logging claim's Core side).
        This case trips the group's policy mutant."""
        store, audit = self._automation_store()
        store.add_rule("input", "term", "unreviewed", ADMIN)
        with self.assertRaises(PolicyBlocked):
            store.invoke(
                "cognitive-automation",
                "run this unreviewed migration task now",
                MEMBER)
        records = store.list_requests(MEMBER)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "blocked_input")
        blocked = [e for e in audit.entries()
                   if e["action"] == "invoke_blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["details"]["stage"], "input")


if __name__ == "__main__":
    unittest.main()
