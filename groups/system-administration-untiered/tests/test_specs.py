"""Spec tests for the System Administration untiered set.

Pin the remainder unit, the taxonomy application, and tier
discipline (FedRAMP 'Unknown' as-is, cmmc_tier null). The
founding group's verbatim 8-family taxonomy (AST-parsed out of
its extractor, never re-tuned) fires on none of this set's four
descriptions: the pinned result is 0 claims, reported plainly.
The verbatim proof (the founding singleton's original shipped
claim table reproduced claim-for-claim, 8 claims) is asserted by
the extractor (scratch/extract.py) at extraction time.

Traces to: remainder.json build unit
'untiered:System Administration' (4 forks, all FedRAMP impact
Unknown) and the founding group's spec schema.
"""

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GROUP))

TOTAL_CLAIMS = 0
ZERO_CLAIM_IDS = [
    'FR2700555848',  # Dynatrace — observability prose; no family phrase
    'FR2630354491',  # Freshworks — ITSM/ITOM prose; no family phrase
    'FR2217348295',  # NetApp Cloud Insights — observability prose; no family phrase
    'FR2701457585',  # PDQ — endpoint-management prose; no family phrase
]
FAMILY_COUNTS = {
    'general_support_system': 0,
    'managed_os_and_services': 0,
    'application_delivery': 0,
    'third_party_hosting_platform': 0,
    'control_inheritance': 0,
    'virtualization_enablement': 0,
    'high_availability': 0,
    'restricted_access': 0,
}
EVERY_FORK = [
    'FR2700555848', 'FR2630354491', 'FR2217348295', 'FR2701457585',
]


def load_specs():
    with open(os.path.join(GROUP, 'specs', 'specs.json')) as fh:
        return json.load(fh)


def load_unit_ids():
    with open(os.path.join(ROOT, 'remainder.json')) as fh:
        rem = json.load(fh)
    units = [u for u in rem['build_units']
             if u['unit_id'] == 'untiered:System Administration']
    assert len(units) == 1
    return units[0]['fork_ids']


def normalize(text):
    # The founding group's documented normalization (its
    # ARTIFACTS.md item 1): whitespace runs collapsed to single
    # spaces, ends stripped. The census description in
    # remainder/uncovered.json is the same record's service_desc
    # verbatim; the stored sheet description is its normalized
    # form, exactly as the founding group's sheets store it.
    return re.sub(r'\s+', ' ', text).strip()


class TestMembership(unittest.TestCase):

    def test_specs_cover_exactly_the_remainder_unit(self):
        specs = load_specs()
        self.assertEqual([s['fork_id'] for s in specs],
                         load_unit_ids())

    def test_four_forks(self):
        self.assertEqual(len(load_specs()), 4)
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

    def test_category_is_system_administration(self):
        for s in load_specs():
            self.assertEqual(s['deadramp_category'],
                             'System Administration')

    def test_no_tier_inferred_from_product_name(self):
        # Dynatrace's product name carries "(High)"; the record's
        # impact level is Unknown and the tier stays null. A name
        # does not move a tier.
        by_id = {s['fork_id']: s for s in load_specs()}
        dyn = by_id['FR2700555848']
        self.assertIn('(High)', dyn['product'])
        self.assertEqual(dyn['fedramp_impact_level'], 'Unknown')
        self.assertIsNone(dyn['cmmc_tier'])


class TestClaims(unittest.TestCase):

    def test_total_claims(self):
        total = sum(len(s['functions_claimed'])
                    for s in load_specs())
        self.assertEqual(total, TOTAL_CLAIMS)

    def test_family_counts_all_zero(self):
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
        # The founding rule stores the first matching sentence
        # verbatim; evidence must be an exact substring of the
        # sheet's description. This set has no claims, so the
        # loop is vacuous -- the pin that matters here is
        # test_zero_claim_forks_reported_plainly above; this test
        # keeps the evidence discipline in force if the source
        # dataset ever changes under a re-run.
        for s in load_specs():
            for c in s['functions_claimed']:
                self.assertIn(c['evidence'], s['description'],
                              (s['fork_id'], c['function_id']))

    def test_descriptions_match_census_descriptions_normalized(
            self):
        with open(os.path.join(ROOT, 'remainder',
                               'uncovered.json')) as fh:
            uncovered = json.load(fh)
        rows = uncovered if isinstance(uncovered, list) else \
            uncovered.get('forks', [])
        unc = {r['fork_id']: r['description'] for r in rows
               if 'fork_id' in r}
        for s in load_specs():
            self.assertEqual(s['description'],
                             normalize(unc[s['fork_id']]),
                             s['fork_id'])


if __name__ == '__main__':
    unittest.main()
