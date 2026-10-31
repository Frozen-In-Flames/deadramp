"""Singleton spec integrity and substrate cases for the CRM L1
singleton (DeadRamp Phase 2 remainder, unit
new-singleton:Customer Relations Management (CRM)|L1).

Traces to: UNION-SPEC.md for the CRM L1 singleton. The group's
single fork (Sprinklr, Inc. / Sprinklr CXM for Government (CXM))
was spec'd under the category's EXISTING 18-family taxonomy applied
verbatim — the additions-style extractor (../scratch/extract.py)
parses the TAXONOMY literal out of Group 25's shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed), asserts it equals Group 40's, and reproduces Group 25's
two shipped claim tables exactly (8 claims) before tagging the
newcomer.

The newcomer claims **1 family**: ``ai_scoring``, on its second
sentence ("Sprinklr's AI-backed core platform consists of five
products: ..."). The basis is recorded at its exact weight in
UNION-SPEC.md and ../scratch/ARTIFACTS.md: the sentence asserts an
AI-backed platform; it asserts no scoring, no model, and no ML
function, and the family is Extended in this category — this build
computes no score anywhere. The other 17 families tag nothing.

Citation accounting, pinned: the fork's single census citation
verifies as a strict verbatim substring — it is the description's
FIRST sentence — and tags no family; the claim rests on the second
sentence, which the census did not cite. Verification is not a
claim, in either direction.

The substrate cases exercise the shipped core as the newcomer
would use it: an account/contact registry with interaction records
across the digital channels its first sentence names (chat and
email are substrate channels), found by search and counted by the
report; and a finding whose detail carries a vendor-stated figure
stored verbatim while no score field or scoring aggregate exists
anywhere — the records form of the fork's research/care surface,
with every engine Extended (UNION-SPEC.md). Neither case touches
the breach derivation, so this file adds no failure to the group's
signature ``_is_breached`` drill (tests/README.md).
"""

import ast
import json
import os
import unittest

import crm_helpers as H

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR2035740126"
UNIT_ID = "new-singleton:Customer Relations Management (CRM)|L1"

ALL_FAMILIES = [
    "account_contact_registry",
    "case_service_records",
    "interaction_records",
    "opportunity_pipeline",
    "campaign_lists",
    "guidance_adoption",
    "gap_identification",
    "engagement_tracking",
    "configuration_extensibility",
    "knowledge_base",
    "marketing_automation",
    "ai_scoring",
    "integrations",
    "reporting",
    "access_control",
    "audit_logging",
    "search",
    "hosting_delivery",
]

_S1 = (
    "Sprinklr CXM for Government helps organizations create, "
    "manage, and optimize customer experiences across various "
    "digital channels including social media, messaging, email, "
    "and websites."
)
_S2 = (
    "Sprinklr's AI-backed core platform consists of five "
    "products: Modern Marketing, Modern Advertising, Modern "
    "Research, Modern Care, and Modern Engagement."
)

EXPECTED_CLAIMS = {
    FORK_ID: [("ai_scoring", _S2)],
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


def _parse_taxonomy(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TAXONOMY"
            for t in node.targets
        ):
            return [tuple(item) for item in ast.literal_eval(node.value)]
    raise AssertionError(f"no TAXONOMY literal in {path}")


class TestSingletonSpecIntegrity(unittest.TestCase):
    """UNION-SPEC.md sections 1/2: membership, literal claim
    table, verbatim description and evidence, census citation
    accounting, near-miss pins."""

    def test_single_sheet_and_membership(self):
        """Exactly 1 sheet, and it is exactly the census unit's
        fork for this singleton."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs], [FORK_ID])
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], [FORK_ID])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["build_unit"], UNIT_ID)
        self.assertEqual(census["proposed_category"],
                         "Customer Relations Management (CRM)")

    def test_taxonomy_verbatim_across_tiers(self):
        """The taxonomy applied here is the category's one
        taxonomy: Group 25's and Group 40's extractors carry
        byte-equal TAXONOMY literals (18 families), and every
        claimed family is one of them."""
        tax_l2 = _parse_taxonomy(os.path.join(
            _REPO_ROOT, "groups", "crm-l2", "scratch", "extract.py"))
        tax_l3 = _parse_taxonomy(os.path.join(
            _REPO_ROOT, "groups", "crm-l3", "scratch", "extract.py"))
        self.assertEqual(tax_l2, tax_l3)
        self.assertEqual([t[0] for t in tax_l2], ALL_FAMILIES)
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["function_id"], ALL_FAMILIES)

    def test_literal_claim_table(self):
        """The fork claims exactly ai_scoring, with the pinned
        evidence sentence (its second sentence)."""
        sheet = _load_specs()[0]
        got = [(c["function_id"], c["evidence"])
               for c in sheet["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[FORK_ID])

    def test_zero_claim_set(self):
        """The zero-claim set is the other 17 families of the
        taxonomy — the description fires nothing else, raw hits
        equal claims (1 = 1), and nothing was removed."""
        sheet = _load_specs()[0]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed,
                         set(ALL_FAMILIES) - {"ai_scoring"})

    def test_tier_fields(self):
        """The fork is FedRAMP LI-SaaS / Certified / L1 / SaaS /
        Public Cloud — its actual impact level recorded, not
        rounded to Low. Its source record carries no business
        categories (uncategorized in the source; the DeadRamp
        category is the census proposal), and forks.json files
        it Uncategorized at L1."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["vendor"], "Sprinklr, Inc.")
        self.assertEqual(sheet["product"],
                         "Sprinklr CXM for Government (CXM)")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "CRM")
        with open(os.path.join(_REPO_ROOT, "forks.json")) as fh:
            forks = json.load(fh)
        fork = next(f for f in forks if f["source_url"].rstrip("/")
                    .rsplit("/", 1)[-1] == FORK_ID)
        self.assertEqual(fork["category"],
                         "Uncategorized (none in source)")
        self.assertEqual(fork["cmmc_tier"], "L1")

    def test_description_equals_cached_source(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["description"],
                         _raw_product(FORK_ID)["service_desc"])
        self.assertEqual(sheet["description"], _S1 + " " + _S2)

    def test_evidence_is_verbatim(self):
        """The claim's evidence sentence appears verbatim in the
        fork's own description."""
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citation_verifies_and_tags_nothing(self):
        """Citation accounting: the fork's single census citation
        verifies as a strict verbatim substring — it IS the
        description's first sentence — and it is not the claim's
        evidence: the claim rests on the second sentence, which
        the census did not cite. Verification is not a claim, in
        either direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["citations"], [_S1])
        sheet = _load_specs()[0]
        self.assertIn(_S1, sheet["description"])
        evidences = [c["evidence"] for c in sheet["functions_claimed"]]
        self.assertNotIn(_S1, evidences)
        self.assertEqual(evidences, [_S2])

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the source record carries no
        certified-services block, and the five products named in
        sentence 2 are the fork's OWN product modules ("Sprinklr's
        AI-backed core platform consists of five products") — an
        in-scope enumeration of its own components, not a
        catalogue of third-party hosted applications. Matched
        text is the full text."""
        self.assertEqual(_raw_product(FORK_ID)["certified_services"],
                         [])
        sheet = _load_specs()[0]
        self.assertIn("consists of five products",
                      sheet["description"])

    def test_near_miss_pins_sprinklr(self):
        """Sprinklr: the CX substance is present in its own words;
        the neighbouring families' operative phrases are absent,
        so every other family stays at zero for this fork."""
        desc = _load_specs()[0]["description"]
        low = desc.lower()
        # Substance present (the claim and the gaps):
        self.assertIn("ai-backed", low)
        self.assertIn("customer experiences", low)
        self.assertIn("digital channels", low)
        self.assertIn("modern marketing", low)
        self.assertIn("modern care", low)
        self.assertIn("modern engagement", low)
        self.assertIn("modern research", low)
        # Family tokens absent:
        self.assertNotIn("customer service", low)
        self.assertNotIn("account management", low)
        self.assertNotIn("contact management", low)
        self.assertNotIn("customer records", low)
        self.assertNotIn("customer profiles", low)
        self.assertNotIn("marketing automation", low)
        self.assertNotIn("email delivery", low)
        self.assertNotIn("email campaign", low)
        self.assertNotIn("engagement tracking", low)
        self.assertNotIn("productivity and engagement", low)
        self.assertNotIn("campaign", low)
        self.assertNotIn("knowledge base", low)
        self.assertNotIn("self-service", low)
        self.assertNotIn("dashboard", low)
        self.assertNotIn("audit", low)
        self.assertNotIn("integrat", low)
        self.assertNotIn("hosted cloud solution", low)
        self.assertNotIn("dedicated government environment", low)
        # "Modern Research" is not the search family: the bare
        # word "search" never appears.
        self.assertNotIn("search", low.replace("research", ""))


class TestSingletonSubstrateCases(unittest.TestCase):
    """Substrate cases for the singleton fork (UNION-SPEC.md core
    section). The core is carried; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_sprinklr_channel_interaction_records(self):
        """Sprinklr shape: an account and a contact held by opaque
        reference (Core 1), interaction records across two of the
        digital channels the fork's first sentence names — chat
        and email are substrate channels (Core 3) — found by
        literal search (Core 8) and counted by channel in the
        report (Core 7). The omnichannel engagement engine that
        would run those channels is Extended — nothing here sends
        or posts anything."""
        store, account, contact = H.make_store()
        chat = store.record_interaction(
            H.OPERATOR, "chat", "inbound", "Website chat about a "
            "permit question", account_id=account["id"],
            contact_id=contact["id"], outcome="answered")
        mail = store.record_interaction(
            H.OPERATOR, "email", "outbound", "Follow-up summary "
            "sent", account_id=account["id"],
            contact_id=contact["id"], outcome="sent")
        self.assertEqual(chat["channel"], "chat")
        self.assertEqual(mail["channel"], "email")
        found = store.search("permit question", H.VIEWER)
        self.assertEqual([i["id"] for i in found["interactions"]],
                         [chat["id"]])
        report = store.report(H.ADMIN, now="2026-06-15T00:00:00Z")
        self.assertEqual(report["interactions"]["by_channel"]["chat"], 1)
        self.assertEqual(
            report["interactions"]["by_channel"]["email"], 1)
        self.assertEqual(report["accounts"]["total"], 1)
        self.assertEqual(report["contacts"]["total"], 1)

    def test_sprinklr_finding_verbatim_no_score(self):
        """Sprinklr shape: a research finding whose detail carries
        a vendor-stated figure is stored **verbatim** (Core 5) —
        the figure is a record, never parsed or aggregated — and
        no score field or scoring aggregate exists in the finding
        or in the report (the privacy/score scan). The fork's one
        claim (the AI family) is Extended: the models that would
        produce such a figure are not built, and nothing in this
        case computes one."""
        store, account, _contact = H.make_store()
        detail = ("Survey summary: sentiment improved 23 percent "
                  "quarter over quarter (vendor-stated figure).")
        finding = store.create_finding(
            H.OPERATOR, "Channel sentiment summary", detail=detail,
            severity="info", account_id=account["id"],
            source="modern-research")
        self.assertEqual(finding["detail"], detail)

        def _scan(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    for bad in ("score", "rating", "grade",
                                "percent", "average", "sentiment"):
                        self.assertNotIn(bad, k.lower())
                    _scan(v)
            elif isinstance(obj, list):
                for v in obj:
                    _scan(v)

        _scan(finding)
        _scan(store.report(H.ADMIN, now="2026-06-15T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
