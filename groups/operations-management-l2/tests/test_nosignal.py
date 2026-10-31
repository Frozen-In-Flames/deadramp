"""No-signal addition coverage: F1603077867 (SMX Elevate IAP).

Traces to: ADDENDUM.md section 8 and scratch/NOSIGNAL_ARTIFACTS.md.

The remainder census left this fork unclassified -- its cached
marketplace description carries no citable function sentence. The
live-docs research pass (repo-root remainder/nosignal_report.json)
resolved it to Operations Management on SMX's own capability-sheet
sentence, so it joins this group as a 23rd sheet. These tests pin:

- the 22 shipped sheets are first and deep-equal to git HEAD;
- the new sheet's membership fields (Moderate / L2, census category
  "Uncategorized (none in source)" in forks.json, research-assigned
  category Operations Management);
- the sheet schema is the house schema plus exactly the two
  classification fields;
- the description is the remainder/uncovered.json record verbatim;
- the claim table is literally zero (raw hits 3: one third-party
  catalogue exclusion, two removals under the group's scoping
  discipline -- recorded in scratch/NOSIGNAL_ARTIFACTS.md) and the
  group total stays 27 claims;
- the classification fields equal the research report's record,
  and the classification sentence is live-doc evidence, never
  claim evidence (citations are not claims);
- the fork's operations substance rides the shipped substrate
  (directory / project / work records + the workflow registry,
  which never executes) with no core extension.
"""

import json
import os
import subprocess
import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, make_store
from opsmgmt.errors import PermissionDenied
from opsmgmt.store import OpsStore

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_SPECS_REPO_PATH = "groups/operations-management-l2/specs/specs.json"
_UNCOVERED_PATH = os.path.join(_REPO_ROOT, "remainder", "uncovered.json")
_REPORT_PATH = os.path.join(_REPO_ROOT, "remainder", "nosignal_report.json")

FORK_ID = "F1603077867"


def _load_specs():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


def _find_record(node, fork_id):
    if isinstance(node, dict):
        if node.get("fork_id") == fork_id:
            return node
        for v in node.values():
            r = _find_record(v, fork_id)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find_record(v, fork_id)
            if r is not None:
                return r
    return None


class TestNoSignalSpecs(unittest.TestCase):
    """No-signal spec integrity, traced to ADDENDUM.md section 8."""

    def test_specs_file_has_23_sheets_and_shipped_22_deep_equal_git_head(self):
        """23 sheets total; the first 22 deep-equal the git HEAD
        specs file exactly (ids, claims, evidence -- the append
        changed none of them)."""
        head = subprocess.run(
            ["git", "-C", _REPO_ROOT, "show", f"HEAD:{_SPECS_REPO_PATH}"],
            capture_output=True, text=True, check=True).stdout
        shipped = json.loads(head)
        self.assertEqual(len(shipped), 22)
        specs = _load_specs()
        self.assertEqual(len(specs), 23)
        self.assertEqual(specs[:22], shipped)

    def test_nosignal_membership_is_exactly_the_resolved_fork(self):
        """The appended sheet is F1603077867 (SMX Elevate IAP),
        Moderate / L2 / FedRAMP Certified, joining under the
        research-assigned category Operations Management."""
        s = _load_specs()[22]
        self.assertEqual(s["fork_id"], FORK_ID)
        self.assertEqual(s["vendor"], "SMX (Formerly Smartronix)")
        self.assertEqual(s["product"],
                         "Elevate Intelligent Automation Platform (IAP)")
        self.assertEqual(s["service_model"], "['PaaS']")
        self.assertEqual(s["fedramp_impact_level"], "Moderate")
        self.assertEqual(s["cmmc_tier"], "L2")
        self.assertEqual(s["authorization_status"], "FedRAMP Certified")
        self.assertEqual(s["deadramp_category"], "Operations Management")

    def test_nosignal_sheet_schema_is_house_plus_classification_fields(self):
        """The new sheet carries exactly the shipped sheets' key set
        plus classification_evidence / classification_source_url;
        the shipped sheets' key sets are unchanged."""
        specs = _load_specs()
        house_keys = set(specs[0].keys())
        for s in specs[:22]:
            self.assertEqual(set(s.keys()), house_keys)
        self.assertEqual(
            set(specs[22].keys()),
            house_keys | {"classification_evidence",
                          "classification_source_url"})

    def test_nosignal_description_is_the_uncovered_record_verbatim(self):
        """The sheet's description is the fork's cached marketplace
        description of record (remainder/uncovered.json) verbatim,
        and vendor / product agree with that record."""
        with open(_UNCOVERED_PATH) as fh:
            unc = json.load(fh)
        recs = unc if isinstance(unc, list) else unc.get("uncovered", unc)
        rec = [r for r in recs if r.get("fork_id") == FORK_ID][0]
        s = _load_specs()[22]
        self.assertEqual(s["description"], rec["description"])
        self.assertEqual(s["vendor"], rec["vendor"])
        self.assertEqual(s["product"], rec["product"])

    def test_nosignal_claim_table_is_literally_zero(self):
        """The fork claims zero families: the full-text raw pass
        produced 3 hits -- security_services inside a third-party
        ISV catalogue paragraph (excluded), workflow_automation on
        the product-name token and authorization_services on the
        platform's own authorization posture (both removed under
        the group's scoping discipline; full record in
        scratch/NOSIGNAL_ARTIFACTS.md). The group total stays
        27 claims; zero-claim forks are 15 of 23."""
        specs = _load_specs()
        s = specs[22]
        self.assertEqual(s["functions_claimed"], [])
        self.assertEqual(
            sum(len(x["functions_claimed"]) for x in specs), 27)
        self.assertEqual(
            sum(1 for x in specs if not x["functions_claimed"]), 15)

    def test_classification_fields_match_the_nosignal_report(self):
        """classification_evidence / classification_source_url equal
        the research report's record for this fork (status resolved,
        existing category Operations Management)."""
        with open(_REPORT_PATH) as fh:
            report = json.load(fh)
        rec = _find_record(report, FORK_ID)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["status"], "resolved")
        self.assertEqual(rec["category_proposal"], "Operations Management")
        self.assertIs(rec["is_new_category"], False)
        s = _load_specs()[22]
        self.assertEqual(s["classification_evidence"],
                         rec["evidence_sentence"])
        self.assertEqual(s["classification_source_url"],
                         rec["source_url"])

    def test_classification_evidence_is_not_claim_evidence(self):
        """Citations are not claims: the classification sentence
        comes from SMX's live capability sheet -- it is not a
        substring of the cached description -- and it serves as
        evidence for no claim in any sheet of this group."""
        specs = _load_specs()
        s = specs[22]
        self.assertNotIn(s["classification_evidence"], s["description"])
        for x in specs:
            for c in x["functions_claimed"]:
                self.assertNotEqual(c["evidence"],
                                    s["classification_evidence"])


class TestNoSignalSubstrate(unittest.TestCase):
    """The fork's substance rides the shipped union (ADDENDUM.md
    section 8): no core extension was warranted."""

    def test_smx_substrate_case_registry_holds_its_operations_shape(self):
        """Substrate case for F1603077867. SMX's own prose describes
        provisioning, monitoring, security, and lifecycle
        management of multi-cloud platforms -- operations work the
        union's substrate holds as records: a tenant organization,
        a project, and work orders under a registered workflow
        definition. Registering the platform-lifecycle workflow
        definition executes nothing (a matching work order keeps
        its state), versioning works, workflow writes stay
        admin-only, and the store exposes no execution entry point
        through which the platform's operations could run -- the
        operations engine itself is Extended (ADDENDUM section 8).
        """
        store, person, organization, project = make_store()
        wo = store.create_work_order(
            OPERATOR, "task", "SMX Elevate platform lifecycle work")
        wf = store.create_workflow(
            ADMIN, "elevate-platform-lifecycle-" + FORK_ID, "task",
            "on create", "route for review")
        store.update_workflow(
            wf["id"], ADMIN, action_text="route to queue")
        self.assertEqual(store.get_workflow(wf["id"], ADMIN)["version"], 2)
        after = store.get_work_order(wo["id"], OPERATOR)
        self.assertEqual(after["status"], "open")
        with self.assertRaises(PermissionDenied):
            store.create_workflow(
                OPERATOR, "operator-wf", "task", "t", "a")
        for name in ("execute_workflow", "run_workflow",
                     "execute", "run_automation", "sync",
                     "connect", "create_integration",
                     "register_integration", "invoke_connector"):
            self.assertFalse(hasattr(OpsStore, name), name)


if __name__ == "__main__":
    unittest.main()
