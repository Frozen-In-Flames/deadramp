"""Additions: the 18 remainder forks of unit `addition:cybersecurity-l2`.

Traces to: ADDENDUM.md (the additions contract for this group) and
UNION-SPEC.md (the taxonomy, the 11 core functions, and the Extended
dispositions the additions inherit unchanged).

The 18 forks were spec'd under the group's EXISTING 25-family
taxonomy, applied verbatim by scratch/additions_extract.py (which
asserts its taxonomy triples equal scratch/extract.py's before
tagging). This module pins the outcome and exercises the substrate
each fork's claims presuppose:

- The spec sheet count (72 = 54 original + 18 additions), the unit
  membership and order, and the per-fork claim table are pinned
  literally, so any taxonomy drift or silent spec edit fails here.
- Every claim's evidence sentence is a verbatim substring of that
  fork's own description in the same sheet (truncated evidence is a
  verbatim prefix).
- For each fork, the records form its Core / Core-substrate claims
  presuppose is exercised end-to-end in the store: findings ingested
  under the fork's product as source, triaged, and retrieved by
  search; asset-criticality rescoring, the risk register, and
  control assessment where the fork claims those families.
- The three zero-claim forks (Login.gov, Proofpoint TAP, Qualys) are
  pinned at zero claims — not hidden — and still exercised as finding
  sources, because findings are source-attributed records: the
  register accepts their output without the forks having claimed the
  substrate.
"""

import json
import os
import unittest

from cyber_helpers import ANALYST, fresh_store, ingest_sample_finding
from cyber_helpers import make_asset
from cyber.audit import AuditLog
from cyber.store import score_finding

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

# The unit's membership, in unit order (remainder.json build_units).
UNIT_IDS = [
    "FR2104942200", "FR2031936863", "FR1814168113", "F1605107897",
    "FR1823149273", "FR1829538820", "FR1718334757", "F1511167634",
    "F1512167750", "F1301101857", "FR2301844932", "FR1913470600",
    "FR1720461312", "FR1819168894", "F1508207205", "FR1821062403",
    "FR2110342613", "FR1731347234",
]

# The pinned claim table: fork_id -> function_ids in taxonomy order,
# exactly as tagged by the verbatim taxonomy (ADDENDUM.md §2).
EXPECTED_CLAIMS = {
    "FR2104942200": ["identity_access", "fraud_identity", "ai_ml",
                     "encryption_feature"],
    "FR2031936863": ["vuln_management", "detection_response",
                     "threat_intel", "compliance_grc", "risk_scoring",
                     "cloud_saas_security", "network_security",
                     "app_security", "asset_inventory", "ai_ml",
                     "reporting_dashboards", "access_control_feature",
                     "api_integration", "automation"],
    "FR1814168113": ["network_security"],
    "F1605107897": ["network_security", "insider_dlp", "ai_ml",
                    "encryption_feature", "api_integration",
                    "automation"],
    "FR1823149273": ["identity_access"],
    "FR1829538820": [],
    "FR1718334757": ["identity_access", "fraud_identity",
                     "risk_scoring", "access_control_feature",
                     "automation"],
    "F1511167634": ["detection_response", "identity_access",
                    "insider_dlp", "endpoint_management",
                    "reporting_dashboards", "audit_logging",
                    "access_control_feature", "encryption_feature",
                    "api_integration"],
    "F1512167750": ["identity_access", "api_integration"],
    "F1301101857": ["app_security"],
    "FR2301844932": ["cloud_saas_security", "api_integration"],
    "FR1913470600": ["endpoint_detection", "detection_response",
                     "threat_intel", "identity_access",
                     "cloud_saas_security", "network_security",
                     "app_security", "phishing_awareness",
                     "insider_dlp", "asset_inventory", "ai_ml",
                     "reporting_dashboards", "access_control_feature",
                     "api_integration", "automation", "log_telemetry"],
    "FR1720461312": ["insider_dlp", "reporting_dashboards"],
    "FR1819168894": [],
    "F1508207205": [],
    "FR1821062403": ["identity_access", "compliance_grc"],
    "FR2110342613": ["endpoint_management"],
    "FR1731347234": ["ai_ml"],
}

ZERO_CLAIM_IDS = ["FR1829538820", "FR1819168894", "F1508207205"]

# Per-fork substrate case: (source token for findings, search token,
# asset kind). The source is the fork's own product name, as a finding
# produced by that product would be attributed.
FORK_CASES = {
    "FR2104942200": ("Acuant COFRS", "Acuant", "application"),
    "FR2031936863": ("Armis AFE", "Armis", "network"),
    "FR1814168113": ("Authentic8 Silo", "Silo", "application"),
    "F1605107897": ("Cisco Cloudlock", "Cloudlock", "cloud"),
    "FR1823149273": ("Duo Federal", "Duo", "application"),
    "FR1829538820": ("Login.gov", "Login.gov", "application"),
    "FR1718334757": ("ID.me Identity Gateway", "ID.me", "application"),
    "F1511167634": ("Kiteworks", "Kiteworks", "server"),
    "F1512167750": ("Okta IDaaS", "Okta", "application"),
    "F1301101857": ("Fortify On Demand", "Fortify", "application"),
    "FR2301844932": ("Orca Security", "Orca", "cloud"),
    "FR1913470600": ("Palo Alto Networks GCS", "Palo Alto", "network"),
    "FR1720461312": ("Proofpoint Email Protection", "Proofpoint Email",
                     "application"),
    "FR1819168894": ("Proofpoint TAP", "TAP", "application"),
    "F1508207205": ("Qualys Cloud Platform", "Qualys", "cloud"),
    "FR1821062403": ("Saviynt EIC", "Saviynt", "application"),
    "FR2110342613": ("Tanium TC-USG", "Tanium", "workstation"),
    "FR1731347234": ("Zimperium zIPS", "Zimperium", "mobile"),
}


def _load_sheets():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


class TestAdditionSpecSheets(unittest.TestCase):
    """ADDENDUM §1–§2: membership, order, and the pinned claim table."""

    def test_sheet_count_and_unit_membership(self):
        """ADDENDUM §1: specs.json holds 72 sheets — the original 54
        followed by exactly the unit's 18 fork IDs, in unit order,
        each exactly once."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), 72)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), 72)
        self.assertEqual(ids[54:], UNIT_IDS)

    def test_unit_membership_matches_remainder_census(self):
        """ADDENDUM §1: the appended IDs are exactly the fork list of
        build unit `addition:cybersecurity-l2` in remainder.json —
        no more, no fewer."""
        with open(_REMAINDER_PATH) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u["unit_id"] == "addition:cybersecurity-l2"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], UNIT_IDS)
        self.assertEqual(unit[0]["extends_group"], "cybersecurity-l2")

    def test_addition_sheets_carry_group_fields(self):
        """ADDENDUM §1: every addition sheet sits in this group at
        this tier — Cybersecurity & Risk Management, L2, FedRAMP
        Moderate (the tier baseline is unchanged by construction) —
        with a non-empty description of its own."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        for fid in UNIT_IDS:
            sheet = sheets[fid]
            self.assertEqual(sheet["deadramp_category"],
                             "Cybersecurity & Risk Management")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertTrue(sheet["description"].strip())

    def test_pinned_claim_table(self):
        """ADDENDUM §2: the per-fork claims are exactly the pinned
        table — the verbatim taxonomy's output, recorded so any
        future re-tagging or silent edit fails loudly here."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in
                   sheets[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(v) for v in EXPECTED_CLAIMS.values())
        self.assertEqual(total, 67)

    def test_zero_claim_forks_are_pinned_not_hidden(self):
        """ADDENDUM §2: exactly three additions carry zero claims —
        Login.gov, Proofpoint TAP, and Qualys — because their own
        descriptions phrase their function in none of the taxonomy's
        25 patterns (the same floor discipline that left Rapid7
        without a vulnerability claim in the original 54)."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        zero = [fid for fid in UNIT_IDS
                if not sheets[fid]["functions_claimed"]]
        self.assertEqual(zero, ZERO_CLAIM_IDS)

    def test_every_evidence_sentence_is_verbatim(self):
        """UNION-SPEC counting rule: a claim's evidence is the
        fork's own marketplace sentence — a verbatim substring of
        the sheet's description (a truncated evidence is a verbatim
        prefix, marked with an ellipsis)."""
        sheets = _load_sheets()
        for sheet in sheets[54:]:
            # extract.py's sentence rule replaces \r with a space
            # before splitting; evidence is verbatim under that one
            # documented normalization.
            desc = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                ev = claim["evidence"]
                if ev.endswith("..."):
                    self.assertIn(ev[:-3], desc,
                                  (sheet["fork_id"],
                                   claim["function_id"]))
                else:
                    self.assertIn(ev, desc,
                                  (sheet["fork_id"],
                                   claim["function_id"]))


class TestAdditionSubstrate(unittest.TestCase):
    """ADDENDUM §3: each addition's Core / Core-substrate claims are
    exercised against the unchanged core; Extended claims presuppose
    only that their output lands here as findings."""

    def _run_fork_case(self, fork_id):
        source, token, kind = FORK_CASES[fork_id]
        claims = EXPECTED_CLAIMS[fork_id]
        audit = AuditLog()
        store = fresh_store(audit=audit)
        asset = make_asset(store, name="addition-asset-" + token,
                           kind=kind, criticality="high")
        finding = ingest_sample_finding(
            store, asset["id"], title="addition finding " + token,
            severity="high", source=source)
        # Deterministic scoring (Core 4): severity weight x asset
        # criticality weight — high on high = 4 * 1.5 = 6.0 / high.
        self.assertEqual((finding["score"], finding["band"]),
                         score_finding("high", "high"))
        self.assertEqual((finding["score"], finding["band"]),
                         (6.0, "high"))
        # Lifecycle (Core 3): new -> triaged is always legal.
        moved = store.transition_finding(finding["id"], "triaged",
                                         actor=ANALYST)
        self.assertEqual(moved["status"], "triaged")
        # Search (Core 7/9): the finding is retrievable by its
        # source attribution.
        hits = store.search(actor=ANALYST, q=token)
        self.assertIn(finding["id"],
                      [f["id"] for f in hits["findings"]])
        if "asset_inventory" in claims:
            # Core 1: a criticality change rescores the asset's
            # findings — high (1.5) -> critical (2.0): 4 * 2.0 = 8.0.
            store.update_asset(asset["id"], actor=ANALYST,
                               criticality="critical")
            after = store.get_finding(finding["id"], actor=ANALYST)
            self.assertEqual((after["score"], after["band"]),
                             (8.0, "critical"))
        if "risk_scoring" in claims:
            # Core 5: the register scores likelihood x impact with
            # the published bands — and nothing else. No model, no
            # hidden input (ADDENDUM §3: the additions bring no
            # computed score of their own).
            risk = store.create_risk(
                "addition risk " + token, "evidenced by " + token,
                4, 5, actor=ANALYST, finding_ids=[finding["id"]])
            self.assertEqual((risk["score"], risk["band"]),
                             (20, "critical"))
        if "compliance_grc" in claims:
            # Core substrate 6: findings link to controls at ingest
            # and assessment state is a query over the catalog.
            linked = ingest_sample_finding(
                store, asset["id"], title="control-linked " + token,
                severity="medium", source=source,
                control_ids=["RA-5"])
            store.assess_control("RA-5", "implemented", actor=ANALYST,
                                 evidence="addition case " + token)
            controls = {c["id"]: c
                        for c in store.list_controls(actor=ANALYST)}
            self.assertEqual(controls["RA-5"]["finding_count"], 1)
            self.assertEqual(controls["RA-5"]["status"], "implemented")
            self.assertEqual(linked["control_ids"], ["RA-5"])
        if "reporting_dashboards" in claims:
            # Core 8: the fork's findings appear in posture counts.
            summary = store.posture_summary(actor=ANALYST)
            self.assertEqual(summary["findings"]["by_severity"]["high"],
                             1)
            self.assertIn(finding["id"],
                          [f["id"] for f in
                           summary["findings"]["top_open"]])
        if "audit_logging" in claims:
            # Core 11: the mutations above are on the append-only
            # trail under their contract action names.
            actions = [e["action"] for e in audit.entries()]
            self.assertIn("finding_ingest", actions)
            self.assertIn("finding_transition", actions)
        # Return the stored record, not the ingest-time snapshot.
        return store, asset, store.get_finding(finding["id"],
                                               actor=ANALYST)

    def test_every_addition_fork_against_the_substrate(self):
        """ADDENDUM §3: all 18 additions, one subTest each — finding
        ingestion, scoring, lifecycle, and search for every fork,
        plus the Core surfaces its own claims name (asset rescoring,
        risk register, control assessment, posture, audit)."""
        for fork_id in UNIT_IDS:
            with self.subTest(fork=fork_id):
                self._run_fork_case(fork_id)

    def test_zero_claim_forks_still_land_as_finding_sources(self):
        """ADDENDUM §2/§3: Login.gov, Proofpoint TAP, and Qualys
        claimed nothing, so nothing is presupposed — but their
        output (auth events, email detections, scan results) is
        source-attributed record data, and the register takes it
        without inventing a claim for them."""
        for fork_id in ZERO_CLAIM_IDS:
            with self.subTest(fork=fork_id):
                store, asset, finding = self._run_fork_case(fork_id)
                self.assertEqual(finding["status"], "triaged")
                self.assertEqual(EXPECTED_CLAIMS[fork_id], [])

    def test_armis_full_surface_case(self):
        """ADDENDUM §3: Armis (14 claims, the broadest addition)
        exercises every Core surface in one flow — its VIPR Pro
        claim set is literally the substrate's shape: consolidated
        findings, an asset register, deterministic risk priority,
        and control-mapped posture."""
        store, asset, finding = self._run_fork_case("FR2031936863")
        summary = store.posture_summary(actor=ANALYST)
        self.assertEqual(summary["assets"]["total"], 1)
        self.assertEqual(summary["risks"]["total"], 1)
        self.assertEqual(summary["controls"]["implemented"], 1)

    def test_bulk_ingest_of_addition_sources_is_atomic(self):
        """Core 2 / ADDENDUM §3: a bulk batch mixing addition
        sources (Orca, Saviynt, Tanium) lands whole or not at all —
        one bad row rejects the batch and consumes no ids, exactly
        as for the original 54."""
        from cyber.errors import ValidationError
        from cyber_helpers import sample_finding_item
        store = fresh_store()
        asset = make_asset(store)
        items = [
            sample_finding_item(asset["id"], title="orca row",
                                source="Orca Security"),
            sample_finding_item(asset["id"], title="saviynt row",
                                source="Saviynt EIC"),
            sample_finding_item(asset["id"], title="bad row",
                                severity="catastrophic",
                                source="Tanium TC-USG"),
        ]
        with self.assertRaises(ValidationError):
            store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])
        good = store.ingest_findings(items[:2], actor=ANALYST)
        self.assertEqual([f["id"] for f in good],
                         ["find-1", "find-2"])


if __name__ == "__main__":
    unittest.main()
