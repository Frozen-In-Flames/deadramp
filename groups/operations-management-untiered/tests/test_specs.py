"""Spec-sheet tests for the Operations Management untiered set.

Pins the census membership (remainder.json build unit
``untiered:Operations Management``), the tier discipline (every sheet
records the source's FedRAMP impact level "Unknown" and
``cmmc_tier: null`` — no baseline is asserted for these forks because
the source publishes none), and the adjudicated claim tables produced
by scratch/extract.py under the founding group's taxonomy verbatim.
"""

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GROUP))
SPECS = os.path.join(GROUP, 'specs', 'specs.json')
REMAINDER = os.path.join(ROOT, 'remainder.json')
UNIT_ID = 'untiered:Operations Management'

EXPECTED_TOTAL_CLAIMS = 2
EXPECTED_CLAIMS_BY_FORK = {
    'FR2628943629': ['inspections_field_ops'],   # IVM SmartHub
    'FR2630447318': ['integrations'],            # Boltline
}
EXPECTED_ZERO_CLAIM = {
    'FR2701457595', 'FR2631054482', 'FR2701256060', 'FR2630354487',
    'FR2630354492', 'FR2631054487', 'FR2634659083', 'FR2631258127',
    'FR2628647241', 'FR2628650874', 'FR2632436493', 'FR2428039108',
    'FR2634659087', 'FR2633841585', 'FR2310051488', 'FR2701247935',
    'FR2316433331', 'FR2628943630',
}


def load_specs():
    with open(SPECS) as fh:
        return json.load(fh)


def unit_fork_ids():
    with open(REMAINDER) as fh:
        rem = json.load(fh)
    units = [u for u in rem['build_units'] if u['unit_id'] == UNIT_ID]
    assert len(units) == 1, units
    return units[0]['fork_ids']


class TestSpecSheets(unittest.TestCase):

    def test_exactly_twenty_sheets(self):
        self.assertEqual(len(load_specs()), 20)

    def test_membership_matches_census_unit_exactly(self):
        sheet_ids = {s['fork_id'] for s in load_specs()}
        self.assertEqual(sheet_ids, set(unit_fork_ids()))
        self.assertEqual(len(unit_fork_ids()), 20)

    def test_tier_discipline_every_sheet(self):
        for s in load_specs():
            self.assertIsNone(s['cmmc_tier'], s['fork_id'])
            self.assertEqual(s['fedramp_impact_level'], 'Unknown',
                             s['fork_id'])

    def test_every_sheet_in_category(self):
        for s in load_specs():
            self.assertEqual(s['deadramp_category'],
                             'Operations Management', s['fork_id'])

    def test_every_claim_evidence_is_verbatim(self):
        # The check applies the founding extractor's documented
        # normalization — carriage returns become spaces before
        # sentence-splitting (groups/operations-management-l2/
        # scratch/extract.py) — rather than being weakened: evidence
        # strings were produced from the normalized text, so the
        # membership test runs against the same normalized text.
        for s in load_specs():
            desc = s['description'].replace('\r', ' ')
            for c in s['functions_claimed']:
                self.assertIn(c['evidence'], desc,
                              (s['fork_id'], c['function_id']))

    def test_total_claims_literal(self):
        total = sum(len(s['functions_claimed']) for s in load_specs())
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)

    def test_claim_tables_by_fork_literal(self):
        for s in load_specs():
            got = [c['function_id'] for c in s['functions_claimed']]
            self.assertEqual(
                got, EXPECTED_CLAIMS_BY_FORK.get(s['fork_id'], []),
                s['fork_id'])

    def test_zero_claim_set_literal(self):
        zero = {s['fork_id'] for s in load_specs()
                if not s['functions_claimed']}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM)
        self.assertEqual(len(zero), 18)


if __name__ == '__main__':
    unittest.main()
