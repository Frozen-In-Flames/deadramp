"""No-signal addition (FR2700754078, CloudFit): spec integrity
and one substrate case.

Traces to: ADDENDUM.md for this set. This fork sat in the
remainder census's ``no-signal-set``: its cached marketplace
description is managed-platform prose (census: citations [],
``no_signal`` "prose_only", ``platform_general`` true), so the
census could not cite a function for it. Its category was
resolved afterwards by the live-docs research pass
(``remainder/nosignal_report.json``): System Administration, on
the vendor's own Managed Services sentence from its homepage
(https://cloudfitsoftware.com/), because the vendor's prose
emphasizes managed services performed -- the census's recorded
managed-platform boundary. That sentence is pinned here as the
sheet's *classification* citation -- kept distinct from claim
evidence, and in fact asserted NOT to occur in the cached
description.

Spec'd under the category's EXISTING 8-family taxonomy applied
verbatim -- the no-signal extractor (scratch/
nosignal_extract.py) imports the set extractor's functions
(taxonomy AST-parsed out of the founding group's extractor,
never executed, never re-typed) and, before tagging, reproduces
both the founding singleton's shipped claim table (8 claims)
and this set's 4 shipped claim tables (0 each) exactly.
CloudFit claims **zero** families: no taxonomy pattern occurs
in its description -- its managed-platform substance (a managed
federal cloud environment, application hosting, monitoring,
operational support) is asserted in vocabulary the founding
fork's exact phrases do not hold. The zero-claim outcome is
pinned here, not hidden, with the near-miss substance asserted
present in the description.
"""

import json
import os
import re
import subprocess
import unittest

from sysadmin_helpers import (
    ADMIN, MEMBER, fresh_store, make_org,
)

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

UNIT_ORDER = [
    "FR2700555848",  # Dynatrace -- Dynatrace Platform for FedRAMP Class D (High)
    "FR2630354491",  # Freshworks -- Freshworks for Government
    "FR2217348295",  # NetApp -- Cloud Insights
    "FR2701457585",  # PDQ -- PDQ for Government
]
NOSIGNAL_ID = "FR2700754078"  # CloudFit Software, LLC -- CloudFit Federal Platform

# The literal claim table for the no-signal fork: it claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {NOSIGNAL_ID: []}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _normalize(text):
    # The founding group's documented normalization (its
    # ARTIFACTS.md item 1): whitespace runs collapsed to single
    # spaces, ends stripped.
    return re.sub(r"\s+", " ", text).strip()


class TestNoSignalSpecIntegrity(unittest.TestCase):
    """ADDENDUM.md: membership, shipped-sheet immutability, the
    literal zero-claim table, verbatim description, tier
    discipline on the new sheet, and the classification
    citation pins."""

    def test_sheet_count_and_order(self):
        """5 sheets: the shipped 4 in unit order, then the
        no-signal sheet."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         UNIT_ORDER + [NOSIGNAL_ID])

    def test_shipped_sheets_deep_equal_git_head(self):
        """The 4 previously shipped sheets are deep-equal to git
        HEAD -- the append changed none of them."""
        head = subprocess.run(
            ["git", "-C", _REPO_ROOT, "show",
             "HEAD:groups/system-administration-untiered/specs/"
             "specs.json"],
            capture_output=True, text=True, check=True).stdout
        head_specs = json.loads(head)
        self.assertEqual(len(head_specs), 4)
        self.assertEqual(_load_specs()[:4], head_specs)

    def test_membership_is_the_nosignal_fork(self):
        """The appended sheet is exactly CloudFit, the fork the
        census left in its no-signal set (citations [],
        no_signal flagged)."""
        specs = _load_specs()
        sheet = _sheet(specs, NOSIGNAL_ID)
        self.assertEqual(sheet["vendor"], "CloudFit Software, LLC")
        self.assertEqual(sheet["product"],
                         "CloudFit Federal Platform")
        self.assertEqual(
            sheet["source_url"],
            "https://www.fedramp.gov/marketplace/products/"
            "FR2700754078/")
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn(NOSIGNAL_ID, unit["fork_ids"])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == NOSIGNAL_ID)
        self.assertTrue(census["no_signal"])
        self.assertEqual(census["citations"], [])

    def test_tier_discipline_on_the_new_sheet(self):
        """Tier stays null: the source publishes no impact level
        for this fork (Unknown), so the sheet records Unknown
        and cmmc_tier null, exactly like the set's sheets, and
        draws no CMMC equivalence."""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertEqual(sheet["deadramp_category"],
                         "System Administration")
        self.assertEqual(sheet["authorization_status"],
                         "Initial Implementation")
        self.assertEqual(sheet["service_model"], ["SaaS", "PaaS"])

    def test_literal_claim_table_zero(self):
        """CloudFit claims zero families; pinned."""
        specs = _load_specs()
        got = [c["function_id"]
               for c in _sheet(specs, NOSIGNAL_ID)[
                   "functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[NOSIGNAL_ID])

    def test_set_totals_unchanged(self):
        """The no-signal addition adds no claims: the set total
        stays 0 and all 5 forks now carry zero claims."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 0)
        self.assertEqual(
            sum(1 for s in specs if not s["functions_claimed"]), 5)

    def test_description_equals_cached_sources(self):
        """The sheet's description is the fork's own cached
        marketplace description under the founding
        normalization -- identical in the raw dataset and in
        remainder/uncovered.json."""
        with open(os.path.join(_REPO_ROOT, "raw",
                               "data_dump.json")) as fh:
            dump = json.load(fh)
        found = {}

        def walk(node):
            if isinstance(node, dict):
                if node.get("id") == NOSIGNAL_ID and \
                        "service_desc" in node:
                    found.update(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(dump)
        raw_desc = found["service_desc"]
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "uncovered.json")) as fh:
            unc = json.load(fh)
        urec = next(r for r in unc if r["fork_id"] == NOSIGNAL_ID)
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["description"],
                         _normalize(raw_desc))
        self.assertEqual(sheet["description"],
                         _normalize(urec["description"]))

    def test_classification_fields_match_report(self):
        """The sheet's classification citation is exactly the
        live-docs report's entry: the verbatim sentence and its
        URL from remainder/nosignal_report.json, category
        System Administration, status resolved, not a new
        category. The sentence is the vendor's homepage prose,
        NOT marketplace text: it does not occur in the cached
        description, which is what keeps the classification
        citation distinct from claim evidence."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "nosignal_report.json")) as fh:
            report = json.load(fh)
        rep = next(r for r in report if r["fork_id"] == NOSIGNAL_ID)
        self.assertEqual(rep["status"], "resolved")
        self.assertEqual(rep["category_proposal"],
                         "System Administration")
        self.assertFalse(rep["is_new_category"])
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["classification_evidence"],
                         rep["evidence_sentence"])
        self.assertEqual(sheet["classification_source_url"],
                         rep["source_url"])
        self.assertEqual(sheet["classification_source_url"],
                         "https://cloudfitsoftware.com/")
        self.assertNotIn(sheet["classification_evidence"],
                         sheet["description"])

    def test_all_claim_evidence_verbatim(self):
        """Every claim's evidence, set-wide, is a verbatim
        substring of its own fork's description (vacuous for
        this set's empty tables, run anyway)."""
        for sheet in _load_specs():
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"],
                              sheet["description"])

    def test_near_miss_pins_cloudfit(self):
        """CloudFit: managed-platform substance is present;
        every family phrase is absent."""
        desc = _sheet(_load_specs(), NOSIGNAL_ID)["description"]
        # Substance present (the near-misses).
        self.assertIn("managed federal cloud environment", desc)
        self.assertIn("application hosting capabilities", desc)
        self.assertIn("hosting customer SaaS applications", desc)
        self.assertIn("identity management", desc)
        self.assertIn("operational support", desc)
        self.assertIn("monitoring", desc)
        # Family phrases absent (case-sensitive, as tagged).
        self.assertNotIn("General Support System (GSS)", desc)
        self.assertNotIn("full management of the OS and services",
                         desc)
        self.assertNotIn("application delivery", desc)
        self.assertNotIn("third-party cloud hosting platforms",
                         desc)
        self.assertNotIn("inherits controls from the CSP", desc)
        self.assertNotIn("virtualization", desc)
        self.assertNotIn("Highly Available (HA)", desc)
        self.assertNotIn("only available to organizations who "
                         "contract", desc)


class TestNoSignalSubstrateCase(unittest.TestCase):
    """One substrate case for the no-signal fork (ADDENDUM.md).
    The core is unchanged; the case runs the fork's described
    surface -- a CloudFit-operated managed platform hosting a
    customer SaaS application, with operational support -- through
    the records forms it presupposes: a managed system record
    (Core 2), an application record on it (Core 3), and a service
    request whose overdue status derives at read (Core 4/5)."""

    def test_cloudfit_managed_platform_records(self):
        store = fresh_store()
        org = make_org(store, ref="HOSTED-AGENCY-1",
                       label="Hosted Agency Systems")
        store.add_member(ADMIN, org["id"], "erin")
        system = store.create_system(
            MEMBER, org["id"], ref="CFP-PLAT-1",
            label="CloudFit managed platform environment",
            kind="platform_service", platform_ref="AZURE-GOV")
        # The managed-system shape is pinned: exactly nine keys,
        # and the hosting platform is an opaque reference only --
        # no hostname, address, or credential field exists.
        self.assertEqual(
            set(system.keys()),
            {"id", "org_id", "ref", "label", "kind",
             "platform_ref", "state", "created_by", "created_utc"})
        app = store.create_application(
            MEMBER, org["id"], system["id"], ref="CUST-APP-1",
            label="Customer SaaS application")
        self.assertEqual(app["system_id"], system["id"])
        request = store.create_request(
            MEMBER, org["id"], system["id"],
            application_id=app["id"], request_kind="support",
            summary="Operational support for hosted application",
            due_date="2026-06-10")
        before = store.get_request(MEMBER, request["id"],
                                   as_of="2026-06-05")
        self.assertFalse(before["overdue"])
        after = store.get_request(MEMBER, request["id"],
                                  as_of="2026-06-15")
        self.assertTrue(after["overdue"])
        # The summary derives its overdue count at the real read
        # clock, under which the June 2026 due date is already
        # past (the carried suite's recorded reading).
        summary = store.organization_summary(MEMBER, org["id"])
        self.assertEqual(summary["requests_overdue"], 1)


if __name__ == "__main__":
    unittest.main()
