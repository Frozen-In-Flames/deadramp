"""Remainder additions — unit addition:cybersecurity-l1 (1 fork).

Traces to: the addendum for HackerOne / HackerOne Continuous
Security Testing Platform (FR1919750997), appended to the shipped
Cybersecurity & Risk Management L1 group under its existing
25-family taxonomy applied verbatim. The newcomer is a ZERO-CLAIM
fork: its three-sentence marketplace description — a vulnerability
disclosure and bug-bounty platform description — produces no raw
hit across any of the 25 families, so its sheet claims nothing and
the pins below are pins on an absence: sheet count and append
order, unit membership against ../../remainder.json, the literal
(empty) claim table, the originals' claim tables reproduced
exactly, the census citations (verified as text; both tag
nothing), the near-miss pins, and the group's updated totals.
Two substrate cases exercise the shipped Core in the shape the
fork's described function presupposes — researcher-reported
findings entering the register, being scored by the published
deterministic formula, triaged, and counted in posture — the
records substrate, carried not claimed. The first substrate case
trips under the group's severity-blind scoring mutant.
"""

import json
import os
import unittest

from cyber_helpers import (ANALYST, fresh_store, ingest_sample_finding,
                           make_asset, sample_finding_item)
from cyber.errors import ValidationError

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR1919750997"
ORIGINAL_IDS = ["FR2529359931", "FR2600167032", "FR2605341343",
                "FR2604952842", "FR1817874315"]
ALL_FAMILIES = [
    "vuln_management", "endpoint_detection", "detection_response",
    "threat_intel", "identity_access", "fraud_identity",
    "compliance_grc", "risk_scoring", "data_protection",
    "cloud_saas_security", "network_security", "app_security",
    "phishing_awareness", "insider_dlp", "asset_inventory",
    "endpoint_management", "ai_ml", "reporting_dashboards",
    "audit_logging", "access_control_feature", "encryption_feature",
    "api_integration", "automation", "log_telemetry", "secure_enclave",
]
ORIGINAL_CLAIMS = {
    "FR2529359931": ["compliance_grc", "ai_ml"],
    "FR2600167032": ["compliance_grc", "risk_scoring",
                     "reporting_dashboards", "api_integration",
                     "automation"],
    "FR2605341343": ["compliance_grc", "ai_ml"],
    "FR2604952842": ["reporting_dashboards"],
    "FR1817874315": ["identity_access", "phishing_awareness",
                     "reporting_dashboards"],
}


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
        """6 sheets: the original 5 in shipped order, newcomer last."""
        ids = [r["fork_id"] for r in _load_specs()]
        self.assertEqual(ids, ORIGINAL_IDS + [FORK_ID])

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork list."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:cybersecurity-l1"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertIn(FORK_ID, [r["fork_id"] for r in _load_specs()])

    def test_literal_claim_table_newcomer_is_empty(self):
        """The newcomer claims exactly nothing under the verbatim
        taxonomy — zero raw hits across all 25 families."""
        self.assertEqual(_sheet(FORK_ID)["functions_claimed"], [])

    def test_original_claim_tables_unchanged(self):
        """The originals' shipped claim tables stand exactly as
        shipped (the extractor's reproduction proof, pinned):
        2 / 5 / 2 / 1 / 3 claims, 13 in total."""
        for fork_id, expected in ORIGINAL_CLAIMS.items():
            claims = [c["function_id"]
                      for c in _sheet(fork_id)["functions_claimed"]]
            self.assertEqual(claims, expected, fork_id)

    def test_zero_claim_set_is_the_whole_taxonomy(self):
        """Every one of the 25 families is unclaimed by the newcomer."""
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        self.assertEqual(claimed, set())
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_registry_fields_as_published(self):
        """Sheet fields record the source as published: LI-SaaS at
        L1, FedRAMP Certified, SaaS / Public Cloud, empty business
        categories; forks.json files the fork as uncategorized and
        the census assignment recorded in deadramp_category is
        Cybersecurity & Risk Management."""
        sheet = _sheet(FORK_ID)
        self.assertEqual(sheet["vendor"], "HackerOne")
        self.assertEqual(
            sheet["product"],
            "HackerOne Continuous Security Testing Platform")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Cybersecurity & Risk Management")

    def test_census_citations_verify_but_tag_nothing(self):
        """Both census citations are verbatim description text — the
        description's first two sentences — and neither is a claim's
        evidence, because there are no claims (verification is not
        a claim)."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "class_all.json")) as fh:
            cls = json.load(fh)
        rows = cls if isinstance(cls, list) else cls.get(
            "classifications", [])
        entry = [r for r in rows if r.get("fork_id") == FORK_ID]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["proposed_category"],
                         "Cybersecurity & Risk Management")
        citations = entry[0]["citations"]
        self.assertEqual(len(citations), 2)
        sheet = _sheet(FORK_ID)
        for cit in citations:
            self.assertIn(cit, sheet["description"])
        self.assertTrue(sheet["description"].startswith(citations[0]))

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the text yet tag
        no family: 'Vulnerability Disclosure' / 'vulnerability
        discovery' without a scanning/management/assessment object
        (vuln_management); 'detect unknown security vulnerabilities'
        with no threat/SOC token (detection_response); the word
        'testing' appears nowhere in the description — it lives
        only in the product's name, which is never matched
        (app_security); 'access to the world's largest community'
        with no identity/authentication or access-control token
        (identity_access, access_control_feature); 'remote, internet
        based' with no contiguous 'remote access'
        (endpoint_management); and no 'risk' token anywhere
        (risk_scoring)."""
        desc = _sheet(FORK_ID)["description"]
        self.assertIn("Vulnerability Disclosure", desc)
        self.assertIn("vulnerability discovery", desc)
        self.assertIn("detect unknown security vulnerabilities", desc)
        self.assertNotIn("testing", desc.lower())
        self.assertIn("Security Testing",
                      _sheet(FORK_ID)["product"])
        self.assertIn("access to the world", desc)
        self.assertIn("remote, internet based", desc)
        self.assertNotIn("remote access", desc)
        self.assertNotIn("risk", desc.lower())
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        for fam in ("vuln_management", "detection_response",
                    "app_security", "identity_access",
                    "access_control_feature", "endpoint_management",
                    "risk_scoring"):
            self.assertNotIn(fam, claimed)

    def test_group_totals(self):
        """Updated union: 6 forks, 13 claims (unchanged), 5 of 6
        claiming, exactly 1 zero-claim fork; the two leading
        families (compliance_grc, reporting_dashboards) are still
        claimed by exactly 3 of 6, and the group's composition is
        Low 4 + LI-SaaS 2."""
        rows = _load_specs()
        total = sum(len(r["functions_claimed"]) for r in rows)
        claiming = sum(1 for r in rows if r["functions_claimed"])
        zero = [r["fork_id"] for r in rows if not r["functions_claimed"]]
        self.assertEqual(total, 13)
        self.assertEqual(claiming, 5)
        self.assertEqual(zero, [FORK_ID])
        for fam in ("compliance_grc", "reporting_dashboards"):
            n = sum(1 for r in rows for c in r["functions_claimed"]
                    if c["function_id"] == fam)
            self.assertEqual(n, 3, fam)
        levels = [r["fedramp_impact_level"] for r in rows]
        self.assertEqual(levels.count("Low"), 4)
        self.assertEqual(levels.count("LI-SaaS"), 2)


class TestHackerOneSubstrate(unittest.TestCase):
    """The described function's shape on the shipped Core. The fork
    claims no family, so these cases exercise the records substrate
    its disclosure function presupposes — researcher-reported
    findings landing in the same register scanner output lands in,
    carried not claimed."""

    def test_researcher_findings_scored_triaged_and_counted(self):
        """A disclosure-programme flow: a public-facing asset is
        registered; a critical researcher report and an info
        researcher report are ingested — severity moves the score
        under the published formula (10.0/critical vs 2.0/low on a
        critical asset; this is the assertion the severity-blind
        mutant breaks) — the critical report is triaged and
        assigned, and posture reports counts only: 2 findings, one
        per severity bucket, the critical one on top."""
        store = fresh_store()
        asset = make_asset(store, name="public-web-portal",
                           kind="application", criticality="critical")
        crit = ingest_sample_finding(
            store, asset["id"], title="Stored XSS in account settings",
            severity="critical", source="researcher-disclosure")
        info = ingest_sample_finding(
            store, asset["id"], title="Verbose server banner",
            severity="info", source="researcher-disclosure")
        self.assertEqual((crit["score"], crit["band"]),
                         (10.0, "critical"))
        self.assertEqual((info["score"], info["band"]), (2.0, "low"))
        crit = store.transition_finding(crit["id"], "triaged",
                                        actor=ANALYST)
        crit = store.assign_finding(crit["id"], "bob", actor=ANALYST)
        self.assertEqual(crit["status"], "triaged")
        self.assertEqual(crit["assignee"], "bob")
        summary = store.posture_summary(actor=ANALYST)
        self.assertEqual(summary["findings"]["total"], 2)
        self.assertEqual(summary["findings"]["by_severity"]["critical"], 1)
        self.assertEqual(summary["findings"]["by_severity"]["info"], 1)
        self.assertEqual(summary["findings"]["top_open"][0]["id"],
                         crit["id"])

    def test_bulk_disclosure_batch_atomic_and_control_linked(self):
        """A researcher's batch of reports enters atomically and
        links to controls at ingest (RA-5 carries both); a second
        batch containing one malformed row is rejected whole —
        nothing is created and the register is unchanged."""
        store = fresh_store()
        asset = make_asset(store, name="api-gateway", kind="cloud",
                           criticality="high")
        items = [
            sample_finding_item(asset["id"], title="IDOR on invoices",
                                severity="high",
                                source="researcher-disclosure",
                                control_ids=["RA-5"]),
            sample_finding_item(asset["id"], title="Missing rate limit",
                                severity="medium",
                                source="researcher-disclosure",
                                control_ids=["RA-5"]),
        ]
        created = store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(len(created), 2)
        controls = {c["id"]: c
                    for c in store.list_controls(actor=ANALYST)}
        self.assertEqual(controls["RA-5"]["finding_count"], 2)
        bad = items + [sample_finding_item(asset["id"],
                                           title="Bogus severity row",
                                           severity="severe",
                                           source="researcher-disclosure")]
        with self.assertRaises(ValidationError):
            store.ingest_findings(bad, actor=ANALYST)
        self.assertEqual(
            len(store.list_findings(actor=ANALYST)), 2)


if __name__ == "__main__":
    unittest.main()
