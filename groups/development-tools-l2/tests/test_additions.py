"""Remainder additions — unit ``addition:development-tools-l2``
(see ADDENDUM.md).

Traces to: the 4 previously uncategorized forks appended to this
group's spec sheets by ``scratch/additions_extract.py`` — Cloud.gov,
Copado GovCloud, FGC DevSecOps, Unqork for Government — spec'd under
the group's existing 17-family taxonomy (Group 17's, via Group 29)
applied verbatim.

Two halves:

- **Spec integrity.** Sheet count and unit order, membership
  against ``../../remainder.json``, the literal per-fork claim
  table, verbatim evidence, the zero-claim fork (Unqork) and the
  twelve zero-claim families pinned (not hidden), the near-miss
  pins (Copado's reversed "continuous deployment and continuous
  integration" is not the family's "continuous integration and
  delivery"; FGC's "integrates them together" is not "integrates
  with"; Cloud.gov's SSP/ATO prose is not a KSI or access-control
  phrase; Unqork's lone verb "build" is not a CI claim), and the
  wording artifact in Copado's visual claim, which stands.
- **Substrate cases.** One case per addition fork against the
  unchanged core, exercising the records forms its claims
  presuppose: environment + deployment records for a platform's
  provisioned environments (Cloud.gov), build/release/deployment
  records for a Salesforce DevOps pipeline (Copado), a landing-zone
  environment with a deployment bound into it (FGC), and — for the
  zero-claim fork — the project/issue records any application
  platform presupposes, including the lifecycle gate (Unqork).
  Records only: nothing is provisioned, executed, or deployed.
"""

import json
import os
import re
import unittest

from devtools.errors import ValidationError

import devtools_helpers as H
from devtools_helpers import ADMIN, DEVELOPER, make_store

_GROUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ROOT = os.path.abspath(os.path.join(_GROUP_DIR, "..", ".."))
CATEGORY = "Development Tools"
UNIT_ID = "addition:development-tools-l2"

ORIGINAL_IDS = ["FR2427142353", "FR2120962552"]
UNIT_IDS = [
    "F1607067912",   # 18F - 18F Cloud.gov / CG-TTS - Cloud.Gov
    "FR2200507410",  # Copado / Copado GovCloud
    "FR1912051231",  # TechTrend, Inc. / Federal GovCloud (FGC) DevSecOps
    "FR2125561001",  # Unqork, Inc. / Unqork for Government
]

# The literal claim table the taxonomy produces for the additions,
# in taxonomy order per sheet. Pinned so any taxonomy drift — or
# any hand-edit of a sheet — fails the suite.
EXPECTED_CLAIMS = {
    "F1607067912": ["hosted_platform"],
    "FR2200507410": ["ci_pipeline", "visual_modeling", "api_integrations"],
    "FR1912051231": ["ci_pipeline", "landing_zones", "hosted_platform"],
    "FR2125561001": [],
}

ZERO_CLAIM_FORKS = {"FR2125561001"}

# Families no addition claims, pinned rather than left implicit.
ZERO_CLAIM_FAMILIES = [
    "project_collaboration",
    "issue_tracking",
    "code_review",
    "deployment_release",
    "config_as_code",
    "artifact_registry",
    "compliance_ksi",
    "business_automation",
    "content_authoring",
    "access_control",
    "audit_logging",
    "search",
]


def load_sheets():
    with open(os.path.join(_GROUP_DIR, "specs", "specs.json")) as fh:
        return json.load(fh)


def addition_sheets():
    return {s["fork_id"]: s for s in load_sheets()[len(ORIGINAL_IDS):]}


class TestAdditionSpecIntegrity(unittest.TestCase):
    """The appended sheets are exactly the census unit, tagged by
    the group's taxonomy verbatim."""

    def test_sheet_count_and_unit_order(self):
        sheets = load_sheets()
        self.assertEqual(len(sheets), 6)
        self.assertEqual(
            [s["fork_id"] for s in sheets], ORIGINAL_IDS + UNIT_IDS
        )

    def test_membership_matches_remainder_unit(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        unit = next(
            u for u in remainder["build_units"] if u["unit_id"] == UNIT_ID
        )
        self.assertEqual(unit["fork_ids"], UNIT_IDS)
        self.assertEqual(unit["category"], CATEGORY)
        self.assertEqual(unit["tier"], "L2")
        self.assertEqual(unit["extends_group"], "development-tools-l2")

    def test_per_fork_claim_table_is_literal(self):
        sheets = addition_sheets()
        self.assertEqual(set(sheets), set(UNIT_IDS))
        for fid, expected in EXPECTED_CLAIMS.items():
            with self.subTest(fork=fid):
                self.assertEqual(
                    [c["function_id"] for c in sheets[fid]["functions_claimed"]],
                    expected,
                )
        self.assertEqual(sum(len(v) for v in EXPECTED_CLAIMS.values()), 7)

    def test_sheet_fields_and_verbatim_evidence(self):
        for fid, sheet in addition_sheets().items():
            with self.subTest(fork=fid):
                self.assertEqual(sheet["deadramp_category"], CATEGORY)
                self.assertEqual(sheet["cmmc_tier"], "L2")
                self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
                self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
                self.assertTrue(sheet["description"])
                for claim in sheet["functions_claimed"]:
                    # Evidence is the fork's own sentence, verbatim.
                    self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_verify_against_descriptions(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        census = {e["fork_id"]: e for e in remainder["forks"]}
        sheets = addition_sheets()
        checked = 0
        for fid in UNIT_IDS:
            desc = sheets[fid]["description"]
            normalized = re.sub(r"\s+", " ", desc)
            for cite in census[fid].get("citations", []):
                text = cite if isinstance(cite, str) else cite.get("sentence", "")
                self.assertTrue(
                    text in desc or re.sub(r"\s+", " ", text) in normalized,
                    (fid, text),
                )
                checked += 1
        self.assertEqual(checked, 5)

    def test_zero_claim_fork_and_families_are_pinned(self):
        sheets = addition_sheets()
        zero = {
            fid for fid, s in sheets.items() if not s["functions_claimed"]
        }
        self.assertEqual(zero, ZERO_CLAIM_FORKS)
        claimed = {
            c["function_id"]
            for s in sheets.values()
            for c in s["functions_claimed"]
        }
        for family in ZERO_CLAIM_FAMILIES:
            with self.subTest(family=family):
                self.assertNotIn(family, claimed)

    def test_near_miss_pins(self):
        sheets = addition_sheets()
        copado = sheets["FR2200507410"]
        copado_families = [c["function_id"] for c in copado["functions_claimed"]]
        # The bullet reverses the family's phrase — "continuous
        # deployment and continuous integration" is not "continuous
        # integration and delivery": deployment_release does not
        # fire on a description saturated with deployment prose.
        self.assertIn(
            "Continuous deployment and continuous integration",
            copado["description"],
        )
        self.assertIn(
            "Deploying Salesforce metadata to production",
            copado["description"],
        )
        self.assertNotIn("deployment_release", copado_families)
        fgc = sheets["FR1912051231"]
        fgc_families = [c["function_id"] for c in fgc["functions_claimed"]]
        # FGC writes "continuous deployment" where the family's
        # phrase is "continuous integration and delivery", and
        # "integrates them together" where the pattern is
        # "integrates with": neither family fires.
        self.assertIn(
            "continuous integration and continuous deployment",
            fgc["description"],
        )
        self.assertIn("integrates them together", fgc["description"])
        self.assertNotIn("deployment_release", fgc_families)
        self.assertNotIn("api_integrations", fgc_families)
        cloudgov = sheets["F1607067912"]
        cg_families = [c["function_id"] for c in cloudgov["functions_claimed"]]
        # SSP/ATO tooling prose is compliance substance with no
        # family: not a KSI phrase, and "Authority To Operate" is
        # not "authorized (users|personnel|agency)".
        self.assertIn("System Security Plans (SSPs)", cloudgov["description"])
        self.assertIn("Authority To Operate (ATO)", cloudgov["description"])
        self.assertNotIn("compliance_ksi", cg_families)
        self.assertNotIn("access_control", cg_families)
        unqork = sheets["FR2125561001"]
        # The lone verb "build" in "rapidly build robust
        # enterprise-grade software" is not a CI pipeline claim
        # (Group 17's tightening principle), and the description
        # never says "visual": the no-code platform claims nothing.
        self.assertIn("rapidly build robust", unqork["description"])
        self.assertIn("no-code", unqork["description"])
        self.assertEqual(unqork["functions_claimed"], [])

    def test_copado_visual_claim_wording_artifact_stands(self):
        # Copado's visual_modeling claim fires on "visual pipeline
        # configuration" via the family's bare "visual" alternative
        # — a graphical pipeline-configuration editor, thinner than
        # a modeling suite. The claim stands at that weight (Group
        # 17 kept Trisotech's bare-"visual" hit the same way);
        # artifact recorded in ADDENDUM §2, not tuned away.
        copado = addition_sheets()["FR2200507410"]
        visual = next(
            c for c in copado["functions_claimed"]
            if c["function_id"] == "visual_modeling"
        )
        self.assertIn("visual pipeline configuration", visual["evidence"])


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork against the unchanged
    core (Core functions per UNION-SPEC)."""

    def test_cloudgov_environment_and_deployment_records(self):
        # Cloud.gov "enables instant provisioning of services and
        # environments": the records forms are environment records
        # (Core 7) and deployment records binding a project and
        # release to an environment. The build provisions nothing;
        # it holds the records of what a platform provisioned.
        store, project = make_store()
        stage = store.create_environment("cf-stage", ADMIN, tier="staging")
        prod = store.create_environment("cf-prod", ADMIN, tier="production")
        rel = store.create_release(project["id"], "v1.0", ADMIN)
        dep = store.record_deployment(
            prod["id"], project["id"], ADMIN, release_id=rel["id"]
        )
        self.assertEqual(dep["status"], "deployed")
        self.assertEqual(dep["environment_id"], prod["id"])
        self.assertEqual(
            [e["name"] for e in store.list_environments()],
            ["cf-stage", "cf-prod"],
        )
        hits = store.search("Widget", ADMIN)
        self.assertEqual([p["id"] for p in hits["projects"]], [project["id"]])
        self.assertEqual(stage["tier"], "staging")

    def test_copado_pipeline_build_release_deployment_records(self):
        # Copado's CI claim and its QA-to-production deployment
        # prose: the records forms are a build record holding the
        # pipeline configuration as a record (Core 4 — the visual
        # configuration's substrate form; nothing executes), a
        # release record (Core 5), and deployment records from the
        # QA environment to production (Core 7).
        store, project = make_store()
        build = store.record_build(
            project["id"], DEVELOPER, ref="pipeline-main",
            config={"configuration": "visual pipeline configuration",
                    "source": "git"},
        )
        self.assertEqual(build["status"], "succeeded")
        self.assertEqual(build["config"]["source"], "git")
        rel = store.create_release(
            project["id"], "2026.10", DEVELOPER, build_id=build["id"]
        )
        qa = store.create_environment("qa", ADMIN)
        prod = store.create_environment("production", ADMIN)
        store.record_deployment(qa["id"], project["id"], DEVELOPER,
                                release_id=rel["id"])
        dep = store.record_deployment(prod["id"], project["id"], DEVELOPER,
                                      release_id=rel["id"])
        self.assertEqual(dep["release_id"], rel["id"])
        art = store.register_artifact(
            project["id"], "salesforce-metadata", DEVELOPER, content="pkg-bytes"
        )
        self.assertTrue(store.verify_artifact(art["id"], "pkg-bytes", ADMIN))
        self.assertFalse(store.verify_artifact(art["id"], "tampered", ADMIN))

    def test_fgc_landing_zone_environment_and_deployment(self):
        # FGC's landing-zone claim: the records form is an
        # environment record standing for the landing zone (Core 7)
        # with a deployment bound into it; its CI/CD claim is a
        # build record (Core 4). Provisioning the zone itself is
        # Extended (gap 8) and is not performed here.
        store, project = make_store()
        build = store.record_build(
            project["id"], DEVELOPER, ref="cicd-main", status="succeeded"
        )
        zone = store.create_environment(
            "aws-landing-zone", ADMIN, tier="landing-zone"
        )
        rel = store.create_release(
            project["id"], "v2.3", DEVELOPER, build_id=build["id"]
        )
        art = store.register_artifact(
            project["id"], "app-bundle", DEVELOPER, content="bundle"
        )
        dep = store.record_deployment(
            zone["id"], project["id"], DEVELOPER,
            release_id=rel["id"], artifact_id=art["id"],
        )
        self.assertEqual(dep["environment_id"], zone["id"])
        self.assertEqual(dep["artifact_id"], art["id"])
        deps = store.list_deployments(environment_id=zone["id"])
        self.assertEqual([d["id"] for d in deps], [dep["id"]])

    def test_unqork_zero_claim_fork_records_and_lifecycle_gate(self):
        # Unqork claims nothing under the taxonomy, but an
        # application built on any platform presupposes project
        # and work records: a project record (Core 1) and an issue
        # moved through the enforced lifecycle (Core 2). The
        # lifecycle gate is asserted here directly — an illegal
        # open -> resolved jump is rejected and the state is
        # unchanged — so this additions module trips the group's
        # signature mutation drill by design.
        store, project = make_store()
        issue = store.create_issue(
            project["id"], "Application intake form defect", DEVELOPER,
            kind="bug",
        )
        with self.assertRaises(ValidationError):
            store.set_issue_status(issue["id"], "resolved", DEVELOPER)
        self.assertEqual(store.get_issue(issue["id"])["status"], "open")
        store.set_issue_status(issue["id"], "in_progress", DEVELOPER)
        moved = store.set_issue_status(issue["id"], "resolved", DEVELOPER)
        self.assertEqual(moved["status"], "resolved")


if __name__ == "__main__":
    unittest.main()
