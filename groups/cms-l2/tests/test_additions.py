"""Remainder addition (unit addition:cms-l2): spec integrity and
substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 20 (CMS L2). The previously
uncategorized fork (Iron Mountain InSight) was spec'd under the
group's EXISTING 13-family taxonomy applied verbatim -- the
additions extractor parses the TAXONOMY literal out of the shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed) and reproduces the original 4 forks' shipped claim
tables exactly before tagging the newcomer.

The fork claims **zero** families, and that outcome is pinned
here, not hidden. Its entire marketplace description is one
sentence: a "content services platform" that "leverages Machine
Learning (ML) and Artificial Intelligence (AI) to automatically
classify, extract, and enrich physical and digital content." None
of the taxonomy's literal phrases appears in it: no "content
management system" / "digital content management" (content
registry), no "metadata" token, no "search", no "editor", no
"ingest", no "digital documents", and its "cloud-based ...
SaaS solution" phrasing is the delivery-model prose the original
calibration scoped out of platform_hosting. The census citation
for the fork is that same single sentence: it verifies verbatim
and tags nothing -- verification is not a claim. The consequence
is also pinned: the union spec's "no fork has zero claims" floor
does **not** survive the addition (4 of 5 forks claim; the group
total stays 19).

The core is unchanged (the fork claims no family, so no core
extension is presupposed). The substrate cases below exercise the
registry the fork's described surface presupposes: classified /
enriched content lives as item records whose classification and
extraction results are metadata and tags (Core 3/7), physical
content enters as an asset registration record with a checksum
(Core 6), and both are found through metadata search (Core 8).
The classification / extraction / enrichment engines themselves
are Extended (ADDENDUM section 5), not implemented, and nothing
in these cases claims them. The lifecycle case runs an item
through the editorial lifecycle with an editor-author reviewing
their own item, so it trips on the group's signature
approver-guard mutant (see tests/README.md).
"""

import json
import os
import unittest

from cms_helpers import AUTHOR, EDITOR, PUBLISHER, make_store
from cms.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "F1302201919",   # Acquia Inc. -- Acquia Cloud
    "FR2330638488",  # PTFS/Liblime -- Bibliovation/Knowvation
    "FR2220654178",  # Tyler Federal, LLC -- Tyler Federal Cloud Platform (TFCP)
    "FR2501644859",  # Vibrent Health -- Digital Health Research Platform
]
UNIT_ORDER = [
    "FR2031155471",  # Iron Mountain -- Iron Mountain InSight
]

# The literal claim table for the addition: the fork claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {
    "FR2031155471": [],
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description, census citation, near-miss pins."""

    def test_sheet_count_and_order(self):
        """5 sheets: the shipped 4 untouched in place, then the
        addition in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:cms-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[4:]],
                         unit["fork_ids"])

    def test_literal_claim_table_zero(self):
        """The addition fork claims zero families; pinned."""
        specs = _load_specs()
        for fork_id, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in _sheet(specs, fork_id)["functions_claimed"]]
            self.assertEqual(got, expected, fork_id)

    def test_group_totals_unchanged(self):
        """The addition adds no claims: the group total stays 19,
        and exactly 1 of the group's 5 forks -- the newcomer --
        carries zero claims. The union spec's "no fork has zero
        claims" floor does not survive the addition; pinned."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 19)
        zero = [s["fork_id"] for s in specs if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR2031155471"])

    def test_addition_tier_fields(self):
        """The addition is FedRAMP Moderate / Certified / L2 /
        SaaS / Government Community Cloud, so the group stays
        single-tier and the baseline is unchanged. Its source
        record carries no business categories (it was
        uncategorized in the source); the DeadRamp category is
        the census proposal, Content Management System (CMS)."""
        sheet = _sheet(_load_specs(), "FR2031155471")
        self.assertEqual(sheet["vendor"], "Iron Mountain")
        self.assertEqual(sheet["product"], "Iron Mountain InSight")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Content Management System (CMS)")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description, verbatim."""
        with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
            dump = json.load(fh)
        prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        pmap = {p["id"]: p for p in prods}
        sheet = _sheet(_load_specs(), "FR2031155471")
        self.assertEqual(
            sheet["description"],
            (pmap["FR2031155471"].get("service_desc") or "").strip())

    def test_census_citation_verifies_as_substring(self):
        """The fork's 1 census citation verifies as a verbatim
        substring of its own description -- and the citation is
        the description's only sentence, which tags no family
        (see the claim table above). Verification is not a
        claim."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        self.assertEqual(len(census["FR2031155471"]["citations"]), 1)
        desc = _sheet(_load_specs(), "FR2031155471")["description"]
        for cite in census["FR2031155471"]["citations"]:
            self.assertIn(cite, desc)
            self.assertEqual(cite, desc)

    def test_near_miss_pins_insight(self):
        """InSight: content-services / ML-AI substance is present
        in its own words; every family phrase is absent."""
        desc = _sheet(_load_specs(), "FR2031155471")["description"]
        low = desc.lower()
        # Substance present (the gap in ADDENDUM section 5):
        self.assertIn("content services platform", low)
        self.assertIn("automatically classify, extract, and enrich", low)
        self.assertIn("physical and digital content", low)
        self.assertIn("machine learning (ml)", low)
        self.assertIn("artificial intelligence (ai)", low)
        self.assertIn("cloud-based", low)
        # Family phrases absent:
        self.assertNotIn("content management system", low)
        self.assertNotIn("digital content management", low)
        self.assertNotIn("metadata", low)
        self.assertNotIn("search", low)
        self.assertNotIn("editor", low)
        self.assertNotIn("ingest", low)
        self.assertNotIn("digital documents", low)
        self.assertNotIn("cloud platform for building", low)
        self.assertNotIn("leading cloud platform", low)
        self.assertNotIn("records management", low)
        self.assertNotIn("reporting", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section 3).
    The core is unchanged; each case runs the fork's described
    surface through the records form it presupposes."""

    def test_insight_content_records_on_registry_substrate(self):
        """InSight: content under management is a Core 3 item
        record; the classification / enrichment results an engine
        would produce are Core 7 metadata and tag records on that
        item; physical content enters as a Core 6 asset
        registration (checksum + metadata, bytes never retained);
        Core 8 search finds both by metadata value and filename.
        The engines themselves are Extended -- nothing here
        classifies, extracts, or enriches anything."""
        store, site, _section = make_store()
        tag = store.create_tag(EDITOR, "Contract", "contract")
        item = store.create_item(
            AUTHOR, site["id"], "ct-document", "Vendor Contract 2026",
            "vendor-contract-2026", body="Scanned agreement.",
            metadata={"classification": "contract",
                      "extracted_party": "ACME",
                      "source_medium": "physical"},
            tag_ids=[tag["id"]])
        self.assertEqual(item["status"], "draft")
        self.assertEqual(item["metadata"]["classification"], "contract")
        self.assertEqual(item["tag_ids"], [tag["id"]])
        data = b"physical scan bytes"
        asset = store.register_asset(
            AUTHOR, site["id"], "vendor-contract-2026.pdf", "document",
            len(data), data=data)
        self.assertEqual(asset["kind"], "document")
        self.assertNotIn("data", asset)
        by_meta = store.search(EDITOR, "contract")
        self.assertEqual([i["id"] for i in by_meta["items"]], [item["id"]])
        by_name = store.search(EDITOR, "vendor-contract-2026.pdf")
        self.assertEqual([a["id"] for a in by_name["assets"]],
                         [asset["id"]])

    def test_insight_item_lifecycle_author_guard(self):
        """InSight: a content record flows through the Core 4
        editorial lifecycle; the editor who authored it cannot
        approve it (AC-5 separation of duties, the group's
        signature guard -- this case trips under the drill
        mutant), a different reviewer approves, and the publisher
        publishes."""
        store, site, _section = make_store()
        item = store.create_item(
            EDITOR, site["id"], "ct-document", "Insight Brief",
            "insight-brief", body="Brief body.")
        store.submit_item(EDITOR, item["id"])
        with self.assertRaises(PermissionDenied):
            store.approve_item(EDITOR, item["id"])
        self.assertEqual(store.get_item(item["id"], EDITOR)["status"],
                         "in_review")
        approved = store.approve_item(PUBLISHER, item["id"])
        self.assertEqual(approved["status"], "approved")
        published = store.publish_item(PUBLISHER, item["id"])
        self.assertEqual(published["status"], "published")


if __name__ == "__main__":
    unittest.main()
