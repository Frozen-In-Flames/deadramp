"""Singleton spec integrity and substrate cases for the
Development Tools L3-adjacent singleton (DeadRamp Phase 2
remainder, unit new-singleton:Development Tools|L3-adjacent).

The group's single fork is FR2102031769 (Red Hat / Red Hat
OpenShift Service on AWS (ROSA)), spec'd under the category's
17-family taxonomy. It claims exactly 1 family:
``hosted_platform``, on the sentence asserting this offering is a
FedRAMP High baseline, Platform-as-a-Service (PaaS) cloud service.
The other 16 families tag nothing.

Citation accounting, pinned: the fork's census citation (its
"quickly build, deploy, and scale applications" sentence) verifies
as a verbatim substring of the description and tags no family; it
is not the evidence of any claimed function. Verification is not a
claim, in either direction.

The substrate cases exercise the shipped core as the newcomer
would use it: a platform-onboarding flow (project, environment,
deployment, build, release, artifact with checksum verification),
the auditor's separation of duties, and a hash chain that still
verifies after the flow.
"""

import json
import os
import unittest

import devtools_helpers as H
from devtools.access import can
from devtools.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR2102031769"
UNIT_ID = "new-singleton:Development Tools|L3-adjacent"

ALL_FAMILIES = [
    "project_collaboration",
    "issue_tracking",
    "code_review",
    "ci_pipeline",
    "deployment_release",
    "config_as_code",
    "artifact_registry",
    "landing_zones",
    "compliance_ksi",
    "visual_modeling",
    "business_automation",
    "content_authoring",
    "hosted_platform",
    "api_integrations",
    "access_control",
    "audit_logging",
    "search",
]

EVIDENCE = (
    "This offering is a FedRAMP High baseline, Platform-as-a-Service "
    "(PaaS) cloud service for developing and running containerized "
    "applications offered on the FedRAMP authorized AWS GovCloud (US)."
)

EXPECTED_CLAIMS = [("hosted_platform", EVIDENCE)]


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _load_remainder():
    with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
        return json.load(fh)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


class TestSingletonSpecIntegrity(unittest.TestCase):
    """Spec integrity: membership, literal claim table, verbatim
    description and evidence, census citation accounting, tier
    fields, and the 16-family zero-claim set."""

    def test_single_sheet_and_membership(self):
        """Exactly 1 sheet, and its fork_id set equals the census
        unit's fork_ids for this singleton."""
        specs = _load_specs()
        self.assertEqual(len(specs), 1)
        rem = _load_remainder()
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual({s["fork_id"] for s in specs}, set(unit["fork_ids"]))
        self.assertEqual(unit["fork_ids"], [FORK_ID])

    def test_literal_claim_table(self):
        """The fork claims exactly [(hosted_platform)] -- one claim,
        with the pinned evidence sentence."""
        sheet = _load_specs()[0]
        got = [(c["function_id"], c["evidence"])
               for c in sheet["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS)

    def test_evidence_is_verbatim_substring(self):
        """The claim's evidence is a verbatim substring of the
        sheet's description."""
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_description_equals_cached_source(self):
        """The sheet's description equals the cached source
        description (raw/data_dump.json, record FR2102031769,
        service_desc stripped)."""
        sheet = _load_specs()[0]
        self.assertEqual(
            sheet["description"],
            _raw_product(FORK_ID)["service_desc"].strip(),
        )

    def test_sheet_fields(self):
        """The sheet's tier/category fields are exactly the
        singleton's: cmmc_tier L3-adjacent, FedRAMP High,
        FedRAMP Certified, deadramp_category Development Tools."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Development Tools")

    def test_census_citation_verifies_and_is_not_evidence(self):
        """The census citation for this fork (from remainder.json's
        forks entry) is a verbatim substring of the description AND
        is not the evidence of any claimed function."""
        rem = _load_remainder()
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertTrue(census["citations"])
        sheet = _load_specs()[0]
        evidences = [c["evidence"] for c in sheet["functions_claimed"]]
        for citation in census["citations"]:
            self.assertIn(citation, sheet["description"])
            self.assertNotIn(citation, evidences)

    def test_other_16_families_absent(self):
        """The other 16 taxonomy families are all absent from
        functions_claimed."""
        sheet = _load_specs()[0]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, {"hosted_platform"})
        others = set(ALL_FAMILIES) - {"hosted_platform"}
        self.assertEqual(len(others), 16)
        self.assertTrue(others.isdisjoint(claimed))


def _onboarding_flow(store):
    """The platform-onboarding flow, in the order the task names:
    project + environment + deployment + build + release + artifact."""
    project = store.create_project("ROSA Onboarding", H.ADMIN, description="demo")
    env = store.create_environment("prod", H.ADMIN, tier="production")
    dep = store.record_deployment(env["id"], project["id"], H.ADMIN)
    build = store.record_build(project["id"], H.ADMIN, ref="main", status="succeeded")
    release = store.create_release(
        project["id"], "v1.0", H.ADMIN, build_id=build["id"])
    artifact = store.register_artifact(
        project["id"], "rosa-pkg", H.ADMIN, version="1.0", content="payload")
    return project, env, dep, build, release, artifact


class TestSingletonSubstrateCases(unittest.TestCase):
    """Substrate cases in this fork's shape, on the shipped core."""

    def test_platform_onboarding_flow(self):
        """(a) Platform-onboarding flow: create_project +
        create_environment + record_deployment + a build record +
        a release + register_artifact with content, and
        verify_artifact is True for the original content and False
        for tampered content."""
        store = H.fresh_store()
        project, env, dep, build, release, artifact = _onboarding_flow(store)
        self.assertTrue(project["id"].startswith("prj-"))
        self.assertTrue(env["id"].startswith("env-"))
        self.assertEqual(dep["environment_id"], env["id"])
        self.assertEqual(dep["project_id"], project["id"])
        self.assertEqual(dep["status"], "deployed")
        self.assertEqual(build["project_id"], project["id"])
        self.assertEqual(build["status"], "succeeded")
        self.assertEqual(release["project_id"], project["id"])
        self.assertEqual(release["build_id"], build["id"])
        self.assertEqual(artifact["project_id"], project["id"])
        self.assertTrue(store.verify_artifact(artifact["id"], "payload", H.ADMIN))
        self.assertFalse(store.verify_artifact(artifact["id"], "tampered", H.ADMIN))

    def test_auditor_reads_audit_but_cannot_create_project(self):
        """(b) The auditor can read the audit log but create_project
        as AUDITOR raises PermissionDenied."""
        audit_store = H.fresh_store()
        audit_store.create_project("Seed", H.ADMIN)
        # Auditor holds audit_read and can read the trail.
        self.assertTrue(can(H.AUDITOR, "audit_read"))
        entries = audit_store.audit.entries()
        self.assertTrue(entries)
        self.assertTrue(
            any(e["action"] == "project_create" for e in entries))
        with self.assertRaises(PermissionDenied):
            audit_store.create_project("Nope", H.AUDITOR)
        self.assertEqual(
            [p["name"] for p in audit_store.list_projects(H.ADMIN)], ["Seed"])

    def test_audit_chain_verifies_after_flow(self):
        """(c) After the onboarding flow, audit.verify_chain() is
        (True, None)."""
        store = H.fresh_store()
        _onboarding_flow(store)
        self.assertEqual(store.audit.verify_chain(), (True, None))


if __name__ == "__main__":
    unittest.main()
