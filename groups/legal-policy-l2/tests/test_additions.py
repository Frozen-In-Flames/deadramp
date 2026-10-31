"""Remainder additions — spec integrity and substrate coverage for
the 6 forks of build unit ``addition:legal-policy-l2``.

Traces to: ADDENDUM.md (this build) and UNION-SPEC.md. The group's
taxonomy was applied **verbatim** to the newcomers by
``scratch/extract_additions.py`` (which asserts its taxonomy copy
equals the original extractor's before tagging). All 6 forks claim
**zero** of the 11 families: the taxonomy was defined from the
original fork's own description (the Group 1 method) and its
patterns are that fork's own phrases. These tests pin that outcome
as a property of the forks' own texts — not an oversight — and give
each newcomer a substrate case against the existing core, which is
unchanged (core delta: zero functions).
"""

import hashlib
import json
import os
import unittest

import legalpol_helpers as H
from legalpol.errors import ValidationError

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS = os.path.join(_GROUP_ROOT, "specs", "specs.json")

UNIT_ORDER = [
    "F1506246782",
    "F1210161615",
    "F1609267945",
    "F1605027893",
    "FR1800263217",
    "FR2004753002",
]

# The remainder census citations for each fork (remainder.json),
# re-verified verbatim against the cached descriptions at build
# time; pinned here so the sheets' descriptions are checked
# against them.
CENSUS_CITATIONS = {
    "F1506246782": [
        "Complete Discovery Source (CDS) is a pioneer in the "
        "eDiscovery industry, providing litigation technology and "
        "hosting, advisory services, and managed services to "
        "support complex discovery matters."
    ],
    "F1210161615": [
        "Deloitte Evidence Management System (EMS) provides "
        "advanced technology and experienced staff to assist "
        "government agencies responding to requests stemming from "
        "litigation, congressional inquiries, FOIA, investigations, "
        "and other similar use cases."
    ],
    "F1609267945": [
        "DocuSign is a San Francisco- and Seattle-based company "
        "that provides electronic signature technology and Digital "
        "Transaction Management services to facilitate electronic "
        "exchanges of contracts and signed documents."
    ],
    "F1605027893": [
        "DocuSign CLM is a secure contract lifecycle management "
        "product in DocuSign's Agreement Cloud.",
        "DocuSign CLM manages contracts in addition to all other "
        "types of documents across desktop, mobile, and partner "
        "applications like Salesforce.",
    ],
    "FR1800263217": [
        "The Innovative Driven Government Cloud (ID Gov-Cloud) is "
        "a Software as a Service (SaaS) offering that provides "
        "secure and scalable government legal document services "
        "within a compliant cloud environment.",
        "Built on industry-leading technologies Relativity and "
        "Nuix and paired with expert consulting, agencies can "
        "leverage the full scope of eDiscovery services within "
        "one scalable platform, including (but not limited to) "
        "processing, document review, advanced analytics, assisted "
        "review, legal hold services, and production.",
    ],
    "FR2004753002": [
        "When it comes to e-discovery, you need the truth to act "
        "quickly, whether it's understanding your organization's "
        "risk around an internal issue, preparing evidence for "
        "litigation or investigations, working through M&A "
        "activity, or even performing proactive compliance "
        "monitoring.",
        "RelativityOne Government brings the entire e-discovery "
        "process together in one secure and extensible platform, "
        "connected to your organization’s most sensitive data - "
        "and supported by the community of experts you need to "
        "untangle it all.",
    ],
}

# The 11 taxonomy patterns, verbatim from scratch/extract.py (all
# are literal phrases; substring absence is regex absence).
PATTERNS = [
    "AI agent workspace",
    "curated, continuously updated library of federal and state "
    "statutes, regulations, guidance and housing datasets",
    "full-text and semantic search",
    "secure single-use agent sandboxes",
    "code execution",
    "document generation",
    "agency user management",
    "session audit visibility",
    "usage export",
    "identity and access are federated",
    "SaaS AI platform",
]


def load_sheets():
    with open(_SPECS, encoding="utf-8") as fh:
        return json.load(fh)


def recompute_checksum(records):
    """Independent recomputation of the export checksum (mirrors
    tests/test_usage_exports.py)."""
    ordered = sorted(records, key=lambda r: int(r["id"].split("-", 1)[1]))
    canonical = [
        {"id": r["id"], "kind": r["kind"], "quantity": r["quantity"],
         "created_utc": r["created_utc"]}
        for r in ordered
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1–2: membership, schema, and the zero-claim table."""

    def test_seven_sheets_original_first_then_unit_order(self):
        """ADDENDUM §1: specs.json holds the original sheet plus
        exactly the 6 unit forks, in unit order."""
        sheets = load_sheets()
        self.assertEqual(len(sheets), 7)
        self.assertEqual(sheets[0]["fork_id"], "FR2619254906")
        self.assertEqual(len(sheets[0]["functions_claimed"]), 11)
        self.assertEqual([s["fork_id"] for s in sheets[1:]], UNIT_ORDER)

    def test_addition_sheets_claim_zero_families(self):
        """ADDENDUM §2: every newcomer claims zero of the 11
        families under the taxonomy applied verbatim."""
        for sheet in load_sheets()[1:]:
            self.assertEqual(sheet["functions_claimed"], [],
                             sheet["fork_id"])

    def test_verbatim_patterns_absent_from_addition_descriptions(self):
        """ADDENDUM §2: the zero-claim outcome is a property of the
        texts — none of the 11 pattern phrases occurs in any
        newcomer's description."""
        for sheet in load_sheets()[1:]:
            for pattern in PATTERNS:
                self.assertNotIn(pattern, sheet["description"],
                                 (sheet["fork_id"], pattern))

    def test_addition_descriptions_carry_census_citations(self):
        """ADDENDUM §1: each sheet's description is the fork's own
        cached text — the census citation sentences occur in it
        verbatim."""
        for sheet in load_sheets()[1:]:
            for citation in CENSUS_CITATIONS[sheet["fork_id"]]:
                self.assertIn(citation, sheet["description"],
                              sheet["fork_id"])

    def test_addition_sheet_schema_and_tier(self):
        """ADDENDUM §1: the new sheets use the original sheet's
        schema exactly, at the group's tier (Moderate / L2), filed
        under Legal & Policy."""
        sheets = load_sheets()
        schema = set(sheets[0].keys())
        for sheet in sheets[1:]:
            self.assertEqual(set(sheet.keys()), schema)
            self.assertEqual(sheet["deadramp_category"], "Legal & Policy")
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["authorization_status"],
                             "FedRAMP Certified")
            self.assertEqual(sheet["service_model"], ["SaaS"])
            self.assertEqual(sheet["business_categories_in_source"], [])


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)


class TestAdditionSubstrate(AdditionFixture):
    """ADDENDUM §4: one substrate case per newcomer against the
    existing, unchanged core — the records forms these platforms'
    activity takes in an embedding."""

    def test_cds_federal_cloud_document_and_verify(self):
        """F1506246782 (eDiscovery hosting): a hosted matter's
        document is a registry record — metadata + SHA-256, content
        never stored (Core 7/8, SI-7) — verified by content."""
        doc = self.store.register_document(
            self.aid, self.workspace["id"], "CDS-DOC-1", H.DOC_SHA256,
            len(H.DOC_CONTENT), H.MEMBER, kind="uploaded")
        ok = self.store.verify_document(self.aid, doc["id"],
                                        H.DOC_CONTENT, H.MEMBER)
        self.assertTrue(ok["matches"])
        bad = self.store.verify_document(self.aid, doc["id"],
                                         H.DOC_CONTENT + b"x", H.MEMBER)
        self.assertFalse(bad["matches"])

    def test_deloitte_ems_search_digest_only(self):
        """F1210161615 (evidence management): a review search is
        recorded as a digest + result count; the query text appears
        nowhere in the stored record (Core 6, privacy discipline)."""
        search = self.store.save_search(
            self.aid, "EMS-SEA-1", H.QUERY_SHA256, 42, H.MEMBER,
            workspace_id=self.workspace["id"])
        stored = self.store._searches[search["id"]]
        self.assertEqual(stored["query_sha256"], H.QUERY_SHA256)
        self.assertEqual(stored["result_count"], 42)
        for value in stored.values():
            if isinstance(value, str):
                self.assertNotIn(H.QUERY_TEXT, value)

    def test_docusign_esignature_document_and_usage(self):
        """F1609267945 (eSignature): a signed-document exchange is
        recorded as a document record plus usage quantities; the
        report counts them on read (Core 7/9/11). The signing
        engine itself is Extended (ADDENDUM §5)."""
        self.store.register_document(
            self.aid, self.workspace["id"], "DS-DOC-1", H.DOC_SHA256,
            128, H.MEMBER, kind="uploaded")
        self.store.record_usage(self.aid, "DS-USE-1", "document", 3,
                                H.MEMBER)
        report = self.store.agency_report(self.aid, H.MEMBER)
        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["usage_by_kind"], {"document": 3})

    def test_docusign_clm_per_workspace_document_refs(self):
        """F1605027893 (CLM): contract records live per workspace —
        the same doc_ref is unique within a workspace and reusable
        across workspaces (Core 7)."""
        other = H.make_workspace(self.store, self.agency,
                                 workspace_ref="WSP-REF-002",
                                 title="Contracts Workspace")
        self.store.register_document(
            self.aid, self.workspace["id"], "CLM-DOC-1", H.DOC_SHA256,
            64, H.MEMBER, kind="uploaded")
        self.store.register_document(
            self.aid, other["id"], "CLM-DOC-1", H.DOC_SHA256, 64,
            H.MEMBER, kind="uploaded")
        with self.assertRaises(ValidationError):
            self.store.register_document(
                self.aid, self.workspace["id"], "CLM-DOC-1",
                H.DOC_SHA256, 64, H.MEMBER, kind="uploaded")

    def test_idgc_session_execution_records(self):
        """FR1800263217 (IDGC): processing/review activity against
        a matter session is recorded as executions on a non-sandbox
        session, which accepts more than one (Core 3/4)."""
        session = H.make_session(self.store, self.agency,
                                 self.workspace)
        self.store.record_execution(self.aid, session["id"], "IDG-EXE-1",
                                    H.MEMBER, kind="document")
        self.store.record_execution(self.aid, session["id"], "IDG-EXE-2",
                                    H.MEMBER, kind="document")
        recorded = self.store.list_executions(self.aid, session["id"],
                                              H.MEMBER)
        self.assertEqual(len(recorded), 2)
        view = self.store.get_session(self.aid, session["id"], H.MEMBER)
        self.assertFalse(view["sandbox_consumed"])

    def test_relativityone_sandbox_single_use(self):
        """FR2004753002 (RelativityOne Government): a one-shot
        review session is a sandbox session — exactly one execution
        is recorded, the second is rejected whole, and consumption
        is derived on the view only (Core 3/4, signature
        invariant)."""
        sandbox = H.make_session(self.store, self.agency,
                                 self.workspace, sandbox=True)
        self.store.record_execution(self.aid, sandbox["id"], "REL-EXE-1",
                                    H.MEMBER, kind="document")
        with self.assertRaises(ValidationError):
            self.store.record_execution(self.aid, sandbox["id"],
                                        "REL-EXE-2", H.MEMBER,
                                        kind="document")
        stored = self.store._sessions[sandbox["id"]]
        self.assertNotIn("sandbox_consumed", stored)
        view = self.store.get_session(self.aid, sandbox["id"], H.MEMBER)
        self.assertTrue(view["sandbox_consumed"])

    def test_additions_usage_export_checksum(self):
        """ADDENDUM §4 (all six): platform usage across the
        newcomers' activity exports as a manifest whose checksum
        recomputes independently from the records (Core 9/10)."""
        self.store.record_usage(self.aid, "ADD-USE-1", "search", 2,
                                H.MEMBER)
        self.store.record_usage(self.aid, "ADD-USE-2", "execution", 3,
                                H.MEMBER)
        self.store.record_usage(self.aid, "ADD-USE-3", "document", 5,
                                H.MEMBER)
        export = self.store.export_usage(self.aid, "ADD-EXP-1", H.MEMBER)
        records = self.store.list_usage(self.aid, H.MEMBER)
        self.assertEqual(export["record_count"], 3)
        self.assertEqual(export["total_quantity"], 10)
        self.assertEqual(export["checksum"], recompute_checksum(records))


if __name__ == "__main__":
    unittest.main()
