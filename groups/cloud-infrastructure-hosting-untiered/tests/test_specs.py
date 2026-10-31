"""Spec integrity for the Cloud Infrastructure & Hosting untiered
set (DeadRamp Phase 2, remainder — the no-signal resolution's
untiered build unit for the category): membership, tier-null
discipline, the literal claim table, verbatim claim evidence in
the cached description, the taxonomy-verbatim reproduction proof,
the third-party catalogue exclusion, and the classification
fields pinned against remainder/nosignal_report.json.

The set has exactly one member, F1403283529 (Project Hosts Inc. /
GSS One - Azure), whose marketplace record publishes no impact
level: the sheet records fedramp_impact_level "Unknown" and
cmmc_tier null, and this build asserts no baseline and draws no
CMMC equivalence.

The classification-vs-claims split is pinned mechanically: the
live-doc classification sentence does NOT occur in the cached
marketplace description, and no claim's evidence is the
classification sentence — classification and claims are separate
evidence streams and never mix.
"""

import ast
import json
import os
import re
import subprocess
import unittest

GROUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(GROUP))
FOUNDING = os.path.join(REPO, "groups", "cloud-infrastructure-hosting-l2")

FORK_ID = "F1403283529"

EXPECTED_CLAIMS = [
    "multi_tenancy",
    "monitoring_observability",
    "backup_disaster_recovery",
    "managed_operations",
]

SHEET_KEYS = {
    "fork_id", "vendor", "product", "service_model", "deployment_model",
    "fedramp_impact_level", "cmmc_tier", "authorization_status",
    "business_categories_in_source", "deadramp_category", "description",
    "functions_claimed", "classification_evidence",
    "classification_source_url", "source", "source_url",
}

CATALOGUE_MARKER = "partial list of applications"

# The founding group's catalogue machinery, needed to reproduce
# its two SAP claim tables in the proof below.
CATALOGUE_LEADINS = (
    "SAP S/4HANA", "SAP SuccessFactors",
    "SAP Business Technology Platform", "SAP HANA Cloud",
    "SAP Analytics Cloud", "SAP Integrated Business Planning",
    "SAP Fieldglass", "Includes:",
)
CATALOGUE_FORKS = {"F1602257856", "FR1719841002"}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _founding_taxonomy():
    """AST-parse the TAXONOMY literal out of the founding group's
    extractor. Parsed, never executed, never re-typed."""
    path = os.path.join(FOUNDING, "scratch", "extract.py")
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "TAXONOMY"
                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("TAXONOMY literal not found")


def _split_units(description):
    """The founding extractor's unit split, reproduced as method."""
    units = []
    for paragraph in description.split("\n\n"):
        for line in paragraph.split("\n"):
            line = line.strip()
            for marker in ("-", "•"):
                if line.startswith(marker):
                    line = line[len(marker):].strip()
            if not line:
                continue
            protected = line.replace("e.g.", "e\u0001g\u0001")
            for sentence in re.split(r"(?<=[.!?])\s+", protected):
                sentence = sentence.replace("\u0001", ".").strip()
                if sentence:
                    units.append(sentence)
    return units


def _claims_for(taxonomy, description, fork_id=None,
                apply_exclusions=True):
    """The founding claims pass, reproduced as method. For this
    set's fork (fork_id None), the exclusion drops every unit
    after the third-party application-list lead-in; for founding
    forks it drops the SAP catalogue units."""
    units = _split_units(description)
    if apply_exclusions and fork_id in CATALOGUE_FORKS:
        units = [u for u in units if not u.startswith(CATALOGUE_LEADINS)]
    if apply_exclusions and fork_id is None:
        kept = []
        for unit in units:
            if CATALOGUE_MARKER in unit:
                break
            kept.append(unit)
        units = kept
    claimed = []
    for function_id, label, patterns in taxonomy:
        regexes = [re.compile(p) for p in patterns]
        evidence = None
        for unit in units:
            if any(rx.search(unit) for rx in regexes):
                evidence = unit
                break
        if evidence is not None:
            claimed.append({
                "function_id": function_id,
                "function": label,
                "evidence": evidence,
            })
    return claimed


class TestSpecs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = _load(os.path.join(GROUP, "specs", "specs.json"))
        cls.sheet = cls.sheets[0]
        cls.uncovered = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "uncovered.json"))}
        cls.report = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "nosignal_report.json"))}
        cls.registry = {r["source_url"].rstrip("/").rsplit("/", 1)[-1]: r
                        for r in _load(os.path.join(REPO, "forks.json"))}
        cls.remainder = _load(os.path.join(REPO, "remainder.json"))

    def test_membership_exact(self):
        # Exactly one sheet: the set's only fork.
        self.assertEqual([s["fork_id"] for s in self.sheets], [FORK_ID])
        # Census membership: the fork sits in the no-signal-set
        # unit, flagged no_signal with no citations — its category
        # was resolved by the live-doc research pass, not by a
        # tiered census unit.
        unit = next(u for u in self.remainder["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn(FORK_ID, unit["fork_ids"])
        row = next(f for f in self.remainder["forks"]
                   if f["fork_id"] == FORK_ID)
        self.assertTrue(row["no_signal"])
        self.assertEqual(row["citations"], [])
        self.assertEqual(row["build_unit"], "no-signal-set")

    def test_sheet_schema_keys(self):
        self.assertEqual(set(self.sheet.keys()), SHEET_KEYS)

    def test_record_fields(self):
        sheet = self.sheet
        self.assertEqual(sheet["vendor"], "Project Hosts Inc.")
        self.assertEqual(sheet["product"], "GSS One - Azure")
        self.assertEqual(sheet["service_model"], ["PaaS"])
        self.assertEqual(sheet["deployment_model"], "Hybrid Cloud")
        self.assertEqual(
            sheet["source_url"], self.registry[FORK_ID]["source_url"])
        # The census recorded no business function for this fork.
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_tier_null_discipline(self):
        # The source publishes no impact level for this offering:
        # tier stays null, on the sheet and in the registry, and
        # the recorded status is record data, not a claim.
        sheet = self.sheet
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertEqual(sheet["authorization_status"], "FedRAMP In Process")
        self.assertEqual(
            sheet["deadramp_category"], "Cloud Infrastructure & Hosting")
        reg = self.registry[FORK_ID]
        self.assertEqual(reg["fedramp_impact_level"], "Unknown")
        self.assertIsNone(reg["cmmc_tier"])

    def test_description_matches_census_and_cache(self):
        self.assertEqual(
            self.sheet["description"], self.uncovered[FORK_ID]["description"])
        dump = _load(os.path.join(REPO, "raw", "data_dump.json"))
        products = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        record = next(p for p in products
                      if isinstance(p, dict) and p.get("id") == FORK_ID)
        self.assertEqual(self.sheet["description"], record["service_desc"])
        # certified_services is never matched; the trap is empty.
        self.assertEqual(record.get("certified_services"), [])

    def test_literal_claim_table(self):
        actual = [c["function_id"] for c in self.sheet["functions_claimed"]]
        self.assertEqual(actual, EXPECTED_CLAIMS)
        self.assertEqual(len(actual), 4)

    def test_claim_evidence_verbatim_in_description(self):
        for claim in self.sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], self.sheet["description"],
                          claim["function_id"])
            self.assertGreater(len(claim["evidence"]), 0)

    def test_classification_fields_match_report(self):
        row = self.report[FORK_ID]
        self.assertEqual(row["status"], "resolved")
        self.assertEqual(
            row["category_proposal"], "Cloud Infrastructure & Hosting")
        self.assertTrue(row["is_new_category"])
        self.assertEqual(
            self.sheet["classification_evidence"], row["evidence_sentence"])
        self.assertEqual(
            self.sheet["classification_source_url"], row["source_url"])

    def test_classification_and_claims_never_mix(self):
        # The classification sentence does not occur in the cached
        # description at all, and no claim's evidence is the
        # classification sentence.
        self.assertNotIn(
            self.sheet["classification_evidence"], self.sheet["description"])
        for claim in self.sheet["functions_claimed"]:
            self.assertNotEqual(
                claim["evidence"], self.sheet["classification_evidence"])

    def test_taxonomy_verbatim_reproduction_proof(self):
        # Before this set's fork was tagged, the founding taxonomy
        # (AST-parsed, never executed) re-applied by the founding
        # method to the founding group's six cached descriptions
        # reproduced its shipped claim tables exactly, deep-equal
        # against git HEAD. Re-run here as a pin.
        taxonomy = _founding_taxonomy()
        self.assertEqual(len(taxonomy), 17)
        head = subprocess.run(
            ["git", "-C", REPO, "show",
             "HEAD:groups/cloud-infrastructure-hosting-l2/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        founding_sheets = json.loads(head)
        self.assertEqual(len(founding_sheets), 6)
        total = 0
        for sheet in founding_sheets:
            reproduced = _claims_for(
                taxonomy, sheet["description"], fork_id=sheet["fork_id"])
            self.assertEqual(
                reproduced, sheet["functions_claimed"], sheet["fork_id"])
            total += len(reproduced)
        self.assertEqual(total, 34)

    def test_extractor_reproduces_this_sheet(self):
        # The same pass that produced this sheet, re-run in the
        # test, yields the sheet's claim table exactly.
        taxonomy = _founding_taxonomy()
        reproduced = _claims_for(taxonomy, self.sheet["description"])
        self.assertEqual(reproduced, self.sheet["functions_claimed"])

    def test_catalogue_exclusion_removed_nothing(self):
        # The description's final section lists ~50 third-party
        # applications hosted ON the platform (52 units after the
        # lead-in). Excluding them before matching changed no
        # claim: the tables with and without the exclusion are
        # identical, and no claim's evidence is a catalogue unit.
        taxonomy = _founding_taxonomy()
        with_excl = _claims_for(taxonomy, self.sheet["description"])
        without = _claims_for(
            taxonomy, self.sheet["description"], apply_exclusions=False)
        self.assertEqual(with_excl, without)
        self.assertIn("WordPress As a Service", self.sheet["description"])
        for claim in self.sheet["functions_claimed"]:
            self.assertNotIn("WordPress", claim["evidence"])
            self.assertNotIn("AvePoint", claim["evidence"])

    def test_absent_tokens(self):
        text = self.sheet["description"].lower()
        for token in ("kubernetes", "serverless", "docker", "terraform",
                      "ansible", "encrypt", "finops"):
            self.assertNotIn(token, text, token)
        self.assertNotIn(
            "Assessment & Authorization", self.sheet["description"])
        self.assertNotIn(
            "Assessment and Authorization", self.sheet["description"])
        self.assertNotIn("Content Delivery Network",
                         self.sheet["description"])

    def test_near_miss_case_artifact(self):
        # "intrusion prevention" occurs twice in lowercase; the
        # security_services patterns are the founding forks'
        # title-case phrases, so the family fires nothing. The
        # taxonomy was not re-tuned. Recorded, not repaired.
        desc = self.sheet["description"]
        self.assertEqual(desc.count("intrusion prevention"), 2)
        claimed = [c["function_id"] for c in self.sheet["functions_claimed"]]
        self.assertNotIn("security_services", claimed)

    def test_hosting_platform_named_absence(self):
        # The category's centre family fires nothing on this
        # fork's words: "cloud computing environment" is not the
        # family's "cloud environment" phrase, and no hosting
        # pattern occurs. The fork is in the category on its
        # classification citation; the absence is recorded, not
        # repaired.
        desc = self.sheet["description"]
        self.assertIn("multi-tenant PaaS cloud computing environment", desc)
        claimed = [c["function_id"] for c in self.sheet["functions_claimed"]]
        self.assertNotIn("hosting_platform", claimed)
        self.assertNotIn("infrastructure_providers", claimed)
        self.assertIn("Azure Government", desc)

    def test_documented_control_sentences_present(self):
        # The sentences UNION-SPEC's Documented control claims
        # section traces are verbatim substrings of the sheet's
        # description — the tracing is pinned to the fork's own
        # words.
        desc = self.sheet["description"]
        for fragment in (
            "manage access control, authentication, auditing, "
            "monitoring, scanning, patching, configuration "
            "management, malware prevention, intrusion prevention, "
            "incident response, backup, and disaster recovery",
            "performs monthly vulnerability scanning include ACAS "
            "scans, dynamic web app scans and container image scans",
            "all SOC review and analysis of audit logs",
            "incident response reporting, analysis, eradication, "
            "and recovery",
            "manages their 3PAO annual assessments",
            "link controls to artifacts and evidence to speed up "
            "ATO times",
        ):
            self.assertIn(fragment, desc, fragment[:40])


if __name__ == "__main__":
    unittest.main()
