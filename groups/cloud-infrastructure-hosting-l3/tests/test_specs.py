"""Spec integrity for the Cloud Infrastructure & Hosting
L3-adjacent group: membership, tier fields, the literal claim
tables, verbatim claim evidence in the cached descriptions, the
classification fields pinned against
remainder/nosignal_report.json — and the TAXONOMY-VERBATIM proof:
the founding group's 17-family taxonomy is ast-parsed (never
executed) out of BOTH extractors and asserted identical, the
founding group's shipped claim tables are reproduced exactly from
its cached descriptions, and this group's tables are reproduced
from the census descriptions by the same matcher.

The classification-vs-claims split is pinned mechanically: for all
six forks the live-doc classification sentence does NOT occur in
the cached marketplace description, and no claim's evidence is the
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
FOUNDING_GROUP = os.path.join(REPO, "groups",
                              "cloud-infrastructure-hosting-l2")

MEMBERS = [
    "F1211011660",
    "F1208031461A",
    "F1206081363",
    "F1303221956",
    "FR1900048743",
    "FR1801046750",
]

EXPECTED_RECORDS = {
    "F1211011660": ("IBM", "IBM Cloud for Government",
                    ["IaaS", "PaaS"], "Hybrid Cloud",
                    "FedRAMP Certified"),
    "F1208031461A": ("IBM", "IBM Platform Services for Government",
                     ["SaaS", "PaaS"], "Public Cloud",
                     "Agency Authorization In Process"),
    "F1206081363": ("IBM", "SmartCloud for Government",
                    ["IaaS"], "Government Community Cloud",
                    "FedRAMP Certified"),
    "F1303221956": ("IT-CNP", "GovDataHosting Cloud Platform",
                    ["PaaS", "IaaS"], "Hybrid Cloud",
                    "FedRAMP Certified"),
    "FR1900048743": ("Oracle",
                     "Oracle Cloud Infrastructure-Government Cloud",
                     ["IaaS", "PaaS"], "Government Community Cloud",
                     "FedRAMP Certified"),
    "FR1801046750": ("United States Department of the Treasury",
                     "Treasury Cloud (TCloud)",
                     ["IaaS", "PaaS"], "Government Community Cloud",
                     "FedRAMP Certified"),
}

EXPECTED_CLAIMS = {
    "F1211011660": [],
    "F1208031461A": ["multi_tenancy", "monitoring_observability",
                     "identity_access", "resource_optimization",
                     "ai_recommendations"],
    "F1206081363": ["multi_tenancy"],
    "F1303221956": ["multi_tenancy", "monitoring_observability",
                    "backup_disaster_recovery"],
    "FR1900048743": [],
    "FR1801046750": ["hosting_platform", "dedicated_environments",
                     "deployment_configuration",
                     "infrastructure_providers",
                     "monitoring_observability", "security_services",
                     "backup_disaster_recovery", "identity_access",
                     "managed_operations", "account_provisioning"],
}

EXPECTED_HISTOGRAM = {
    "hosting_platform": 1,
    "dedicated_environments": 1,
    "multi_tenancy": 3,
    "deployment_configuration": 1,
    "infrastructure_providers": 1,
    "monitoring_observability": 3,
    "security_services": 1,
    "backup_disaster_recovery": 2,
    "identity_access": 2,
    "managed_operations": 1,
    "resource_optimization": 1,
    "ai_recommendations": 1,
    "account_provisioning": 1,
}

ZERO_CLAIM_FORKS = {"F1211011660", "FR1900048743"}

# Families claimed at the founding tier that claim nothing here.
FAMILIES_SILENT_AT_THIS_TIER = (
    "encryption", "us_operations_residency",
    "compliance_authorization_support", "content_delivery",
)

SHEET_KEYS = {
    "fork_id", "vendor", "product", "service_model", "deployment_model",
    "fedramp_impact_level", "cmmc_tier", "authorization_status",
    "business_categories_in_source", "deadramp_category", "description",
    "functions_claimed", "classification_evidence",
    "classification_source_url", "source", "source_url",
}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _literal_from(path, name):
    """Recover a module-level literal via ast (parsed, never run)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError("%s not found in %s" % (name, path))


def _split_units(description):
    """The house sentence split, as the founding extractor
    documents it."""
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


def _claims_for(taxonomy, catalogue_forks, catalogue_leadins,
                description, fork_id):
    units = _split_units(description)
    if fork_id in catalogue_forks:
        units = [u for u in units
                 if not u.startswith(catalogue_leadins)]
    claimed = []
    for function_id, label, patterns in taxonomy:
        regexes = [re.compile(p) for p in patterns]
        evidence = None
        for unit in units:
            if any(rx.search(unit) for rx in regexes):
                evidence = unit
                break
        if evidence is not None:
            claimed.append({"function_id": function_id,
                            "function": label,
                            "evidence": evidence})
    return claimed


class TestTaxonomyVerbatim(unittest.TestCase):
    """The taxonomy is the founding group's, verbatim — proven,
    not asserted in prose."""

    @classmethod
    def setUpClass(cls):
        founding_extract = os.path.join(
            FOUNDING_GROUP, "scratch", "extract.py")
        cls.founding_extract = founding_extract
        cls.own_extract = os.path.join(GROUP, "scratch", "extract.py")
        cls.taxonomy = _literal_from(founding_extract, "TAXONOMY")
        cls.catalogue_forks = set(
            _literal_from(founding_extract, "CATALOGUE_FORKS"))
        cls.catalogue_leadins = tuple(
            _literal_from(founding_extract, "CATALOGUE_LEADINS"))
        raw = subprocess.run(
            ["git", "-C", REPO, "show",
             "HEAD:groups/cloud-infrastructure-hosting-l2/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        cls.founding = {s["fork_id"]: s for s in json.loads(raw)}

    def test_taxonomy_is_the_founding_literal(self):
        self.assertEqual(len(self.taxonomy), 17)
        self.assertEqual(
            [family[0] for family in self.taxonomy],
            ["hosting_platform", "dedicated_environments",
             "multi_tenancy", "deployment_configuration",
             "infrastructure_providers", "monitoring_observability",
             "security_services", "backup_disaster_recovery",
             "identity_access", "encryption", "managed_operations",
             "us_operations_residency", "resource_optimization",
             "ai_recommendations", "account_provisioning",
             "compliance_authorization_support", "content_delivery"])

    def test_own_extractor_derives_taxonomy_by_ast(self):
        # This group's extractor holds no re-typed taxonomy: its
        # TAXONOMY is the value of a _literal_from call on the
        # founding group's extractor file (ast-parsed, never
        # executed). Pin the derivation mechanism in the source.
        with open(self.own_extract, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("cloud-infrastructure-hosting-l2", source)
        self.assertIn("TAXONOMY = _literal_from(", source)
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "TAXONOMY"
                    for t in node.targets):
                self.assertIsInstance(node.value, ast.Call)

    def test_founding_claim_tables_reproduced_exactly(self):
        # TAXONOMY-VERBATIM PROOF: re-applying the ast-parsed
        # taxonomy to the founding group's six cached descriptions
        # reproduces its shipped claim tables deep-equal.
        self.assertEqual(len(self.founding), 6)
        for fork_id, sheet in self.founding.items():
            got = _claims_for(self.taxonomy, self.catalogue_forks,
                              self.catalogue_leadins,
                              sheet["description"], fork_id)
            self.assertEqual(got, sheet["functions_claimed"], fork_id)

    def test_this_groups_tables_recomputed_from_descriptions(self):
        sheets = _load(os.path.join(GROUP, "specs", "specs.json"))
        for sheet in sheets:
            got = _claims_for(self.taxonomy, self.catalogue_forks,
                              self.catalogue_leadins,
                              sheet["description"], sheet["fork_id"])
            self.assertEqual(got, sheet["functions_claimed"],
                             sheet["fork_id"])


class TestSpecs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = _load(os.path.join(GROUP, "specs", "specs.json"))
        cls.by_id = {s["fork_id"]: s for s in cls.sheets}
        cls.uncovered = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "uncovered.json"))}
        cls.report = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "nosignal_report.json"))}
        cls.registry = {r["source_url"].rstrip("/").rsplit("/", 1)[-1]: r
                        for r in _load(os.path.join(REPO, "forks.json"))}
        raw = subprocess.run(
            ["git", "-C", REPO, "show",
             "HEAD:groups/cloud-infrastructure-hosting-l2/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        cls.founding = {s["fork_id"]: s for s in json.loads(raw)}

    def test_membership_exact(self):
        self.assertEqual(sorted(self.by_id), sorted(MEMBERS))
        self.assertEqual(len(self.sheets), 6)

    def test_sheet_schema_keys(self):
        for sheet in self.sheets:
            self.assertEqual(set(sheet.keys()), SHEET_KEYS, sheet["fork_id"])

    def test_record_fields(self):
        for fork_id, (vendor, product, models, deployment, status) in \
                EXPECTED_RECORDS.items():
            sheet = self.by_id[fork_id]
            self.assertEqual(sheet["vendor"], vendor, fork_id)
            self.assertEqual(sheet["product"], product, fork_id)
            self.assertEqual(sheet["service_model"], models, fork_id)
            self.assertEqual(sheet["deployment_model"], deployment, fork_id)
            self.assertEqual(sheet["authorization_status"], status, fork_id)
            self.assertEqual(
                sheet["source_url"], self.registry[fork_id]["source_url"])

    def test_tier_fields_from_marketplace_record(self):
        for sheet in self.sheets:
            reg = self.registry[sheet["fork_id"]]
            self.assertEqual(sheet["fedramp_impact_level"], "High")
            self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
            # Tier and status are the registry record's, verbatim.
            self.assertEqual(sheet["fedramp_impact_level"],
                             reg["fedramp_impact_level"])
            self.assertEqual(sheet["cmmc_tier"], reg["cmmc_tier"])
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"])
            self.assertEqual(
                sheet["deadramp_category"], "Cloud Infrastructure & Hosting")
            # The census recorded no business function for these forks.
            self.assertEqual(sheet["business_categories_in_source"], [])

    def test_descriptions_match_census_copies(self):
        for fork_id in MEMBERS:
            self.assertEqual(
                self.by_id[fork_id]["description"],
                self.uncovered[fork_id]["description"], fork_id)

    def test_literal_claim_tables(self):
        for fork_id, expected in EXPECTED_CLAIMS.items():
            actual = [c["function_id"]
                      for c in self.by_id[fork_id]["functions_claimed"]]
            self.assertEqual(actual, expected, fork_id)

    def test_claim_totals_and_histogram(self):
        total = sum(len(s["functions_claimed"]) for s in self.sheets)
        self.assertEqual(total, 19)
        histogram = {}
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                histogram[claim["function_id"]] = \
                    histogram.get(claim["function_id"], 0) + 1
        self.assertEqual(histogram, EXPECTED_HISTOGRAM)

    def test_zero_claim_forks_pinned(self):
        zero = {s["fork_id"] for s in self.sheets
                if not s["functions_claimed"]}
        self.assertEqual(zero, ZERO_CLAIM_FORKS)

    def test_claim_evidence_verbatim_in_description(self):
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              (sheet["fork_id"], claim["function_id"]))
                self.assertGreater(len(claim["evidence"]), 0)

    def test_classification_fields_match_report(self):
        for fork_id in MEMBERS:
            sheet = self.by_id[fork_id]
            row = self.report[fork_id]
            self.assertEqual(row["status"], "resolved")
            self.assertEqual(
                row["category_proposal"], "Cloud Infrastructure & Hosting")
            self.assertTrue(row["is_new_category"])
            self.assertEqual(
                sheet["classification_evidence"], row["evidence_sentence"])
            self.assertEqual(
                sheet["classification_source_url"], row["source_url"])

    def test_classification_and_claims_never_mix(self):
        for sheet in self.sheets:
            self.assertNotIn(
                sheet["classification_evidence"], sheet["description"],
                sheet["fork_id"])
            for claim in sheet["functions_claimed"]:
                self.assertNotEqual(
                    claim["evidence"], sheet["classification_evidence"])

    def test_platform_services_duplicate_pair(self):
        # F1208031461A is the High duplicate-authorization sibling
        # of the founding group's F1208031461: a separate offering,
        # spec'd separately. The two records carry the same
        # description, so the claim tables match — and the tiers
        # differ, because the tier comes from each record.
        high = self.by_id["F1208031461A"]
        moderate = self.founding["F1208031461"]
        self.assertEqual(high["description"], moderate["description"])
        self.assertEqual(high["functions_claimed"],
                         moderate["functions_claimed"])
        self.assertEqual(moderate["fedramp_impact_level"], "Moderate")
        self.assertEqual(high["fedramp_impact_level"], "High")
        self.assertNotEqual(high["authorization_status"],
                            moderate["authorization_status"])

    def test_tcloud_high_is_a_distinct_offering(self):
        # FR1801046750 (TCloud-H) and the founding AGENCYWC2
        # (Treasury Cloud Moderate) are separate offerings of the
        # same service family, spec'd separately; the High record's
        # description is its own (a wider service list), and its
        # table differs from the Moderate table.
        high = self.by_id["FR1801046750"]
        moderate = self.founding["AGENCYWC2"]
        self.assertNotEqual(high["description"], moderate["description"])
        self.assertNotEqual(high["functions_claimed"],
                            moderate["functions_claimed"])
        self.assertEqual(len(high["functions_claimed"]), 10)
        self.assertEqual(len(moderate["functions_claimed"]), 12)

    def test_itcnp_prose_assertions_recorded_not_converted(self):
        # IT-CNP's prose asserts a "FedRAMP Class D (High)"
        # certification and support for low/moderate/high systems;
        # the sheet's tier is the marketplace record's High, and
        # the prose is recorded as the fork's assertion.
        sheet = self.by_id["F1303221956"]
        self.assertIn("FedRAMP Class D (High)", sheet["description"])
        self.assertIn("low, moderate, and high impact information "
                      "systems", sheet["description"])
        self.assertEqual(sheet["fedramp_impact_level"], "High")

    def test_families_silent_at_this_tier(self):
        claimed = {c["function_id"] for s in self.sheets
                   for c in s["functions_claimed"]}
        founding_claimed = {c["function_id"]
                            for s in self.founding.values()
                            for c in s["functions_claimed"]}
        for family in FAMILIES_SILENT_AT_THIS_TIER:
            self.assertIn(family, founding_claimed, family)
            self.assertNotIn(family, claimed, family)

    def test_absent_technology_tokens(self):
        for sheet in self.sheets:
            text = sheet["description"].lower()
            for token in ("kubernetes", "serverless", "docker",
                          "terraform", "ansible", "machine learning"):
                self.assertNotIn(token, text, (sheet["fork_id"], token))

    def test_near_miss_tokens_confined(self):
        # "endpoint management" occurs only in the Platform
        # Services bundle (the MaaS360 component; the MDM
        # category's ground, not this one's) and fires no family.
        for sheet in self.sheets:
            text = sheet["description"].lower()
            if sheet["fork_id"] == "F1208031461A":
                self.assertIn("endpoint management", text)
            else:
                self.assertNotIn("endpoint management", text,
                                 sheet["fork_id"])

    def test_near_misses_recorded_not_repaired(self):
        # IBM Cloud for Government: provisioning/orchestration
        # substance, no family phrase — zero claims, pinned.
        ibm_cloud = self.by_id["F1211011660"]
        self.assertIn("automated provisioning",
                      ibm_cloud["description"])
        self.assertIn("orchestration of bare metal",
                      ibm_cloud["description"])
        self.assertEqual(ibm_cloud["functions_claimed"], [])
        # Oracle: platform prose throughout, no family phrase.
        oracle = self.by_id["FR1900048743"]
        self.assertIn("government-community cloud",
                      oracle["description"])
        self.assertEqual(oracle["functions_claimed"], [])
        # IT-CNP identity: the description spells "identity and
        # access management"; the family's pattern is the founding
        # fork's "identity & access management" — no claim.
        itcnp = self.by_id["F1303221956"]
        self.assertIn("identity and access management",
                      itcnp["description"])
        self.assertNotIn("identity_access",
                         [c["function_id"]
                          for c in itcnp["functions_claimed"]])
        # IT-CNP residency: U.S.-persons substance, none of the
        # family's phrases — no claim.
        self.assertIn("continental United States by U.S. persons",
                      itcnp["description"])
        self.assertNotIn("us_operations_residency",
                         [c["function_id"]
                          for c in itcnp["functions_claimed"]])
        # SmartCloud operations: "System Vulnerability Scanning"
        # (capital S) does not fire the family's "Vulnerability
        # scanning" pattern — no managed_operations claim.
        scg = self.by_id["F1206081363"]
        self.assertIn("System Vulnerability Scanning",
                      scg["description"])
        self.assertNotIn("managed_operations",
                         [c["function_id"]
                          for c in scg["functions_claimed"]])
        # TCloud-H tenancy: "multitenant" unhyphenated does not
        # fire the family's "multi-tenant" pattern.
        tcloud = self.by_id["FR1801046750"]
        self.assertIn("multitenant, government-exclusive",
                      tcloud["description"])
        self.assertNotIn("multi_tenancy",
                         [c["function_id"]
                          for c in tcloud["functions_claimed"]])


if __name__ == "__main__":
    unittest.main()
