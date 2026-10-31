"""Spec tests for the GRC untiered set.

Pin the remainder unit, the taxonomy application, and tier
discipline (FedRAMP 'Unknown' as-is, cmmc_tier null). Every claim
traces to the fork's own description sentence under the founding
group's verbatim 14-family taxonomy; the verbatim proof (original
2 forks reproduced claim-for-claim, 14 claims) is asserted by the
extractor (scratch/extract.py) at extraction time.

Traces to: remainder.json build unit
'untiered:Governance, Risk, and Compliance (GRC)' (15 forks, all
FedRAMP impact Unknown) and the founding group's spec schema.
"""

import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GROUP))

TOTAL_CLAIMS = 25
ZERO_CLAIM_IDS = [
    'FR2631258125',  # Certivo — continuously-maintained evidence base; no family phrase
    'FR2633957422',  # Vastian — workflow automation / role-based access controls; newline-broken, no family phrase
    'FR2632558735',  # ACE — "authorization boundaries" / "audit cloud service"; no family phrase
    'FR2700137045',  # RegScale — "continuous controls monitoring" adjacency; flagship GRC, zero claims
    'FR2629068830',  # SunStone — "AO" abbreviation, "analysis workflows"; no family phrase
    'FR2630354484',  # VisualVault — "Compliance and Enforcement" / "configure workflows"; no family phrase
]
FAMILY_COUNTS = {
    'evidence_management': 0,
    'continuous_monitoring': 3,
    'ksi_tracking': 4,
    'vulnerability_remediation': 0,
    'control_framework_compliance': 2,
    'posture_reporting': 0,
    'assessment_authorization': 2,
    'risk_management': 1,
    'policy_management': 6,
    'audit_support': 1,
    'platform_hosting': 0,
    'identity_access_hooks': 0,
    'workflow_automation': 2,
    'api_integrations': 4,
}
EVERY_FORK = [
    'FR2701557058', 'FR2628647239', 'FR2635930439', 'FR2628943633',
    'FR2631258122', 'FR2631258125', 'FR2630354485', 'FR2633957422',
    'FR2631054539', 'FR2632558735', 'FR2700754082', 'FR2700137045',
    'FR2629068830', 'FR2633053629', 'FR2630354484',
]
# The exclusion pass: one raw hit removed, recorded in
# scratch/ARTIFACTS.md — ComplianceAide's only `assessor` evidence
# sits inside the sentence where the offering states it does not
# replace an independent assessor or make authorization decisions.
REMOVED_HITS = [('FR2630354485', 'assessment_authorization')]


def load_specs():
    with open(os.path.join(GROUP, 'specs', 'specs.json')) as fh:
        return json.load(fh)


def load_unit_ids():
    with open(os.path.join(ROOT, 'remainder.json')) as fh:
        rem = json.load(fh)
    units = [u for u in rem['build_units']
             if u['unit_id'] == 'untiered:Governance, Risk, and '
                                 'Compliance (GRC)']
    assert len(units) == 1
    return units[0]['fork_ids']


class TestMembership(unittest.TestCase):

    def test_specs_cover_exactly_the_remainder_unit(self):
        specs = load_specs()
        self.assertEqual([s['fork_id'] for s in specs],
                         load_unit_ids())

    def test_fifteen_forks(self):
        self.assertEqual(len(load_specs()), 15)
        self.assertEqual([s['fork_id'] for s in load_specs()],
                         EVERY_FORK)


class TestTierDiscipline(unittest.TestCase):

    def test_impact_level_unknown_as_in_source(self):
        for s in load_specs():
            self.assertEqual(s['fedramp_impact_level'], 'Unknown',
                             s['fork_id'])

    def test_cmmc_tier_null_everywhere(self):
        for s in load_specs():
            self.assertIsNone(s['cmmc_tier'], s['fork_id'])

    def test_category_is_grc(self):
        for s in load_specs():
            self.assertEqual(
                s['deadramp_category'],
                'Governance, Risk, and Compliance (GRC)')


class TestClaims(unittest.TestCase):

    def test_total_claims(self):
        total = sum(len(s['functions_claimed'])
                    for s in load_specs())
        self.assertEqual(total, TOTAL_CLAIMS)

    def test_family_counts(self):
        counts = {k: 0 for k in FAMILY_COUNTS}
        for s in load_specs():
            for c in s['functions_claimed']:
                counts[c['function_id']] += 1
        self.assertEqual(counts, FAMILY_COUNTS)

    def test_zero_claim_forks_reported_plainly(self):
        zero = [s['fork_id'] for s in load_specs()
                if not s['functions_claimed']]
        self.assertEqual(zero, ZERO_CLAIM_IDS)

    def test_evidence_is_verbatim_description_sentence(self):
        # The GRC founding rule stores the first matching sentence
        # verbatim; evidence must be an exact substring of the
        # sheet's description (no description in this set contains a
        # carriage return, so no normalization applies).
        for s in load_specs():
            for c in s['functions_claimed']:
                self.assertIn(c['evidence'], s['description'],
                              (s['fork_id'], c['function_id']))

    def test_removed_hits_absent(self):
        by_id = {s['fork_id']: s for s in load_specs()}
        for fid, func in REMOVED_HITS:
            claimed = [c['function_id']
                       for c in by_id[fid]['functions_claimed']]
            self.assertNotIn(func, claimed, (fid, func))

    def test_duplicate_pair_claim_tables_identical(self):
        by_id = {s['fork_id']: s for s in load_specs()}
        a, b = by_id['FR2628647239'], by_id['FR2635930439']
        self.assertEqual(a['description'], b['description'])
        self.assertEqual(a['functions_claimed'],
                         b['functions_claimed'])
        self.assertEqual(len(a['functions_claimed']), 4)

    def test_claim_families_are_taxonomy_families(self):
        for s in load_specs():
            for c in s['functions_claimed']:
                self.assertIn(c['function_id'], FAMILY_COUNTS)


if __name__ == '__main__':
    unittest.main()
