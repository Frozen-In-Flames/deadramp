"""Additions: the 2 remainder forks of unit `addition:cybersecurity-l3`.

Traces to: ADDENDUM.md (the additions contract for this group) and
UNION-SPEC.md (the 25-family taxonomy, the 11 core functions, the
High-baseline uplifts, and the Extended dispositions the additions
inherit unchanged).

The 2 forks were spec'd under the group's EXISTING 25-family
taxonomy, applied verbatim by scratch/additions_extract.py (which
parses the taxonomy out of the original scratch/extract.py via ast
and first reproduces the original 16 forks' shipped claim tables
exactly before tagging anyone new). This module pins the outcome and
exercises the substrate each fork's claims presuppose:

- The spec sheet count (18 = 16 original + 2 additions), the unit
  membership and order, and the per-fork claim table are pinned
  literally, so any taxonomy drift or silent spec edit fails here.
- Every claim's evidence sentence is a verbatim substring of that
  fork's own description in the same sheet (truncated evidence is a
  verbatim prefix), and both census citations verify verbatim.
- The one wording-artifact correction (Cisco's endpoint_management)
  and the named near-misses are pinned as absences.
- For each fork, the records form its Core / Core-substrate claims
  presuppose is exercised end-to-end in the store at the High
  baseline: findings ingested under the fork's product as source,
  deterministically scored, triaged, retrieved by search; asset
  rescoring and posture counts where claimed; the hash-chained
  audit trail verifies after the fork's operations.
"""

import json
import os
import unittest

from cyber_helpers import ANALYST, AUDITOR, fresh_store
from cyber_helpers import ingest_sample_finding, make_asset
from cyber.audit import AuditLog
from cyber.errors import PermissionDenied
from cyber.store import score_finding

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")
_CLASS_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder",
                           "class_all.json")

# The unit's membership, in unit order (remainder.json build_units).
UNIT_IDS = ["FR2304757473A", "FR1714261912"]

# The pinned claim table: fork_id -> function_ids in taxonomy order,
# exactly as tagged by the verbatim taxonomy after the one recorded
# correction (ADDENDUM.md §2).
EXPECTED_CLAIMS = {
    "FR2304757473A": ["detection_response", "threat_intel",
                      "identity_access", "network_security",
                      "phishing_awareness", "insider_dlp",
                      "asset_inventory", "ai_ml",
                      "reporting_dashboards", "access_control_feature",
                      "api_integration", "automation"],
    "FR1714261912": ["identity_access", "encryption_feature"],
}

# Per-fork substrate case: (source token for findings, search token,
# asset kind). The source is the fork's own product name, as a finding
# produced by that product would be attributed.
FORK_CASES = {
    "FR2304757473A": ("Cisco Security Cloud for Government", "Cisco",
                      "network"),
    "FR1714261912": ("AuthentX Cloud", "AuthentX", "application"),
}


def _load_sheets():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


class TestAdditionSpecSheets(unittest.TestCase):
    """ADDENDUM §1–§2: membership, order, and the pinned claim table."""

    def test_sheet_count_and_unit_membership(self):
        """ADDENDUM §1: specs.json holds 18 sheets — the original 16
        followed by exactly the unit's 2 fork IDs, in unit order,
        each exactly once."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), 18)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), 18)
        self.assertEqual(ids[16:], UNIT_IDS)

    def test_unit_membership_matches_remainder_census(self):
        """ADDENDUM §1: the appended IDs are exactly the fork list of
        build unit `addition:cybersecurity-l3` in remainder.json —
        no more, no fewer."""
        with open(_REMAINDER_PATH) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u["unit_id"] == "addition:cybersecurity-l3"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], UNIT_IDS)
        self.assertEqual(unit[0]["extends_group"], "cybersecurity-l3")

    def test_addition_sheets_carry_group_fields(self):
        """ADDENDUM §1: every addition sheet sits in this group at
        this tier — Cybersecurity & Risk Management, L3-adjacent,
        FedRAMP High (the tier baseline is unchanged by
        construction) — with a non-empty description of its own."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        for fid in UNIT_IDS:
            sheet = sheets[fid]
            self.assertEqual(sheet["deadramp_category"],
                             "Cybersecurity & Risk Management")
            self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
            self.assertEqual(sheet["fedramp_impact_level"], "High")
            self.assertTrue(sheet["description"].strip())

    def test_pinned_claim_table(self):
        """ADDENDUM §2: the per-fork claims are exactly the pinned
        table — the verbatim taxonomy's output after the one
        recorded correction, recorded so any future re-tagging or
        silent edit fails loudly here."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in
                   sheets[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(v) for v in EXPECTED_CLAIMS.values())
        self.assertEqual(total, 14)

    def test_group_totals_after_additions(self):
        """ADDENDUM §4: the enlarged group is 18 forks and 74 claims
        (60 + 14), with 17 of 18 forks claiming at least one
        function — NetCloud Federal remains the group's only
        zero-claim fork."""
        sheets = _load_sheets()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in sheets), 74)
        zero = [s["fork_id"] for s in sheets
                if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR2626164349"])  # NetCloud Federal
        self.assertNotIn(zero[0], UNIT_IDS)

    def test_cisco_endpoint_management_correction_is_pinned(self):
        """ADDENDUM §2: Cisco's raw endpoint_management match is
        dropped and stays dropped — its only "device management"
        text manages firewall appliances ("cloud-native firewall
        policy and device management"), a network function, not
        endpoint management. The sentence remains in the sheet's
        description; the claim does not."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        cisco = sheets["FR2304757473A"]
        self.assertIn("firewall policy and device management",
                      cisco["description"])
        claimed = [c["function_id"] for c in cisco["functions_claimed"]]
        self.assertNotIn("endpoint_management", claimed)

    def test_named_near_misses_stay_unclaimed(self):
        """ADDENDUM §2: family-adjacent substance that matches no
        pattern earns no claim, pinned per fork — Cisco's compliance
        prose and twice-named CASB (no cloud_saas_security), and
        AuthentX's mandate prose (no compliance_grc), access-
        management wording (no access_control_feature), and
        credentialing substance (no fraud_identity). Neither fork
        claims risk_scoring: no computed score enters with them."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        cisco = [c["function_id"] for c in
                 sheets["FR2304757473A"]["functions_claimed"]]
        authentx = [c["function_id"] for c in
                    sheets["FR1714261912"]["functions_claimed"]]
        for fam in ("compliance_grc", "cloud_saas_security",
                    "vuln_management", "risk_scoring"):
            self.assertNotIn(fam, cisco, fam)
        for fam in ("compliance_grc", "access_control_feature",
                    "fraud_identity", "endpoint_management",
                    "risk_scoring"):
            self.assertNotIn(fam, authentx, fam)

    def test_every_evidence_sentence_is_verbatim(self):
        """UNION-SPEC counting rule: a claim's evidence is the
        fork's own marketplace sentence — a verbatim substring of
        the sheet's description (a truncated evidence is a verbatim
        prefix, marked with an ellipsis)."""
        sheets = _load_sheets()
        for sheet in sheets[16:]:
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

    def test_census_citations_verify_verbatim(self):
        """ADDENDUM §1: the remainder census's starting-point
        citations for these 2 forks (1 each) all verify as verbatim
        substrings of the forks' own cached descriptions — the
        census was verified, not trusted."""
        with open(_CLASS_PATH) as fh:
            census = {r["fork_id"]: r for r in json.load(fh)}
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        checked = 0
        for fid in UNIT_IDS:
            desc = sheets[fid]["description"].replace("\r", " ")
            for cit in census[fid]["citations"]:
                self.assertIn(cit, desc, fid)
                checked += 1
        self.assertEqual(checked, 2)


class TestAdditionSubstrate(unittest.TestCase):
    """ADDENDUM §3: each addition's Core / Core-substrate claims are
    exercised against the unchanged core at the High baseline;
    Extended claims presuppose only that their output lands here as
    findings."""

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
        # The additions claim no scoring family, and no other score
        # exists for their records: this declared formula is the
        # only computation (ADDENDUM §3).
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
        if "reporting_dashboards" in claims:
            # Core 8: the fork's findings appear in posture counts
            # (counts only — posture stores no opinion and computes
            # no aggregate score).
            summary = store.posture_summary(actor=ANALYST)
            self.assertEqual(summary["findings"]["by_severity"]["high"],
                             1)
            self.assertIn(finding["id"],
                          [f["id"] for f in
                           summary["findings"]["top_open"]])
        # High uplift (Core 11, AU-9): the fork's operations are on
        # the hash-chained trail and the chain verifies.
        ok, first_bad = audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("finding_ingest", actions)
        self.assertIn("finding_transition", actions)
        return store, asset, store.get_finding(finding["id"],
                                               actor=ANALYST)

    def test_every_addition_fork_against_the_substrate(self):
        """ADDENDUM §3: both additions, one subTest each — finding
        ingestion, deterministic scoring, lifecycle, search, and
        the High-tier audit chain, plus the Core surfaces each
        fork's own claims name."""
        for fork_id in UNIT_IDS:
            with self.subTest(fork=fork_id):
                self._run_fork_case(fork_id)

    def test_authentx_identity_claims_buy_hooks_not_an_idp(self):
        """ADDENDUM §3: AuthentX's identity_access claim earns the
        substrate's access-control hooks and nothing more — the
        trail AuthentX-attributed operations produced is queryable
        (AU-7), and the auditor role at High, holding audit_read
        only (AC-5), is denied the ingest her fork's identity
        product would perform itself in its own product. IA-2
        stays with the embedding organization; no IdP is built."""
        store, asset, finding = self._run_fork_case("FR1714261912")
        trail = store.audit.query(actor="bob")
        self.assertTrue(trail)
        with self.assertRaises(PermissionDenied):
            ingest_sample_finding(store, asset["id"], actor=AUDITOR,
                                  title="auditor must not ingest",
                                  source="AuthentX Cloud")


if __name__ == "__main__":
    unittest.main()
