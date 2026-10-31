"""Spec tests for the Artificial Intelligence (AI) untiered set.

Pin the remainder unit, the taxonomy application, and tier
discipline (FedRAMP 'Unknown' as-is, cmmc_tier null). Every claim
traces to the fork's own description sentence under the founding
group's verbatim 16-family taxonomy; the verbatim proof (founding
group's current 12 sheets reproduced claim-for-claim, 47 claims,
ids + evidence) is asserted by the extractor (scratch/extract.py)
at extraction time.

Traces to: remainder.json build unit
'untiered:Artificial Intelligence (AI)' (9 forks, all FedRAMP
impact Unknown) and the founding group's spec schema.
"""

import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GROUP))

TOTAL_CLAIMS = 13
ZERO_CLAIM_IDS = [
    'FR2628647242',  # Bland — "AI phone agents" fires nothing; its one raw gateway hit sat inside an explicit negation (removed)
    'FR2632054534',  # Lemma — one-sentence description; "AI workflow orchestration" fires no family
]
FAMILY_COUNTS = {
    'learned_inference': 4,
    'model_gateway': 0,
    'model_governance': 0,
    'usage_metering': 0,
    'audit_logging': 2,
    'access_control': 1,
    'multi_tenancy': 1,
    'guardrails': 1,
    'interaction_records': 0,
    'zero_persistence': 0,
    'evaluation_records': 0,
    'api_integration': 0,
    'agentic_workflows': 3,
    'document_automation': 0,
    'analytics_reporting': 0,
    'contact_center': 1,
}
EVERY_FORK = [
    'FR2633053633', 'FR2633153276', 'FR2632558748', 'FR2632054530',
    'FR2628647242', 'FR2700137035', 'FR2628647238', 'FR2634659079',
    'FR2632054534',
]
EXPECTED_CLAIMS = {
    'FR2633053633': ['audit_logging', 'agentic_workflows'],
    'FR2633153276': ['learned_inference', 'agentic_workflows',
                     'contact_center'],
    'FR2632558748': ['learned_inference'],
    'FR2632054530': ['learned_inference'],
    'FR2628647242': [],
    'FR2700137035': ['multi_tenancy'],
    'FR2628647238': ['audit_logging', 'access_control'],
    'FR2634659079': ['learned_inference', 'guardrails',
                     'agentic_workflows'],
    'FR2632054534': [],
}
# The exclusion pass: one raw hit removed, recorded in
# scratch/ARTIFACTS.md — Bland's only `model providers` evidence
# sits inside the sentence stating customer calls are NOT sent to
# third-party model providers.
REMOVED_HITS = [('FR2628647242', 'model_gateway')]


def load_specs():
    with open(os.path.join(GROUP, 'specs', 'specs.json')) as fh:
        return json.load(fh)


def load_unit_ids():
    with open(os.path.join(ROOT, 'remainder.json')) as fh:
        rem = json.load(fh)
    units = [u for u in rem['build_units']
             if u['unit_id'] == 'untiered:Artificial Intelligence (AI)']
    assert len(units) == 1
    return units[0]['fork_ids']


class TestMembership(unittest.TestCase):

    def test_specs_cover_exactly_the_remainder_unit(self):
        specs = load_specs()
        self.assertEqual([s['fork_id'] for s in specs],
                         load_unit_ids())

    def test_nine_forks(self):
        self.assertEqual(len(load_specs()), 9)
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

    def test_category_is_ai(self):
        for s in load_specs():
            self.assertEqual(s['deadramp_category'],
                             'Artificial Intelligence (AI)')


class TestClaims(unittest.TestCase):

    def test_total_claims(self):
        total = sum(len(s['functions_claimed'])
                    for s in load_specs())
        self.assertEqual(total, TOTAL_CLAIMS)

    def test_literal_claim_tables(self):
        for s in load_specs():
            got = [c['function_id'] for c in s['functions_claimed']]
            self.assertEqual(got, EXPECTED_CLAIMS[s['fork_id']],
                             s['fork_id'])

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
        # The founding evidence rule: evidence is the first matching
        # sentence, verbatim under the documented normalization
        # (carriage returns replaced with spaces before
        # sentence-splitting), or its truncated form (sentence[:397]
        # + '...' when the sentence exceeds 400 characters — the
        # Claude agentic_workflows claim in this set).
        for s in load_specs():
            desc = s['description'].replace('\r', ' ')
            for c in s['functions_claimed']:
                ev = c['evidence']
                self.assertTrue(
                    ev in desc or (ev.endswith('...')
                                   and ev[:-3] in desc),
                    (s['fork_id'], c['function_id']))

    def test_removed_hits_absent(self):
        by_id = {s['fork_id']: s for s in load_specs()}
        for fid, func in REMOVED_HITS:
            claimed = [c['function_id']
                       for c in by_id[fid]['functions_claimed']]
            self.assertNotIn(func, claimed, (fid, func))

    def test_headline_near_misses_stay_unclaimed(self):
        # The founding discipline, pinned: adjective forms the
        # taxonomy does not contain manufacture no claims, even for
        # the set's flagship products.
        by_id = {s['fork_id']: s for s in load_specs()}
        claude = [c['function_id']
                  for c in by_id['FR2633053633']['functions_claimed']]
        self.assertNotIn('learned_inference', claude)
        eleven = [c['function_id']
                  for c in by_id['FR2628647238']['functions_claimed']]
        self.assertNotIn('learned_inference', eleven)
        self.assertNotIn('multi_tenancy', eleven)
        self.assertNotIn('zero_persistence', eleven)

    def test_claim_families_are_taxonomy_families(self):
        for s in load_specs():
            for c in s['functions_claimed']:
                self.assertIn(c['function_id'], FAMILY_COUNTS)


if __name__ == '__main__':
    unittest.main()
