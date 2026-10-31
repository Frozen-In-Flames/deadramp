# Tests — Energy Management L1 singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**74 tests, all passing** (Python 3 standard library `unittest`
only). Each test module's header names the core function, spec
claim, or control family it traces to.

| Module | Covers |
|---|---|
| `test_access.py` | Role/permission matrix (AC family) |
| `test_registries.py` | Customer & provider registries: pinned shapes, no identifier field possible, ref uniqueness |
| `test_auctions.py` | Auction records; status derived at read, never stored; no stored outcome keys; early close |
| `test_bids.py` | Bid records: open-window-only recording, integer-cent prices (floats/bools rejected), immutability, sequence order |
| `test_outcome.py` | **The signature invariant**: lowest bid wins, ties by earliest sequence, outcome derived never stored, finality follows derived status, no ranking produced |
| `test_observations.py` | Price-observation records; integer cents; zero allowed, negatives rejected |
| `test_alerts.py` | Alert subscriptions & alert records; cross-customer subscription guard; alerts recorded, never delivered |
| `test_engagements.py` | Advisory engagement records for the three claimed kinds; verbatim notes; open → closed lifecycle |
| `test_reporting.py` | Search & summary: counts only, latest price per series derived at read, recursive no-score key scan over summaries, outcomes, and stored records |
| `test_audit.py` | Append-only audit log; mutations recorded, failures not; `audit_read` admin-only; JSONL persistence |
| `test_service.py` | REST API over real HTTP: full flow, float price rejected (400), auth failures (401/403), exactly 3 denied attempts audited |
| `test_main_cli.py` | CLI argument handling and demo-user wiring |
| `test_specs.py` | Spec integrity: membership == census unit {FR2014363920}, recorded fields match `forks.json`, taxonomy == the 9 own-description families, evidence verbatim, census citations verify |
| `test_negative_control.py` | The mutation-verified negative control (below) |

## Negative control — mutation-verified

The signature invariant is the outcome derivation: a reverse
auction's winning bid is the **lowest**-priced bid, derived at
read by the single seam `_derive_winner` in `src/energy/store.py`.
An oracle that passes with both min and max is testing that code
ran, not that the lowest bid wins — so the invariant is verified
two ways:

1. **In-tree mutant** (`test_negative_control.py`): the canonical
   outcome expectation is asserted against a run where the
   `_derive_winner` seam is swapped for a mutant selecting the
   *highest*-priced bid (ties by latest sequence). The test asserts
   the canonical check raises `AssertionError` against the mutant,
   and a second test asserts the tie-break arm discriminates too.
2. **External drill** (performed on this tree, recorded in
   `scratch/mutation-run.txt`): `_derive_winner` in the real
   `src/energy/store.py` was patched to select the highest-priced
   bid (`max` in place of `min`, same key), the full suite
   re-run, and the file then restored.

**Drill result: exactly 4 failures out of 74 tests:**

- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`
- `test_outcome.OutcomeTests.test_lowest_bid_wins`
- `test_outcome.OutcomeTests.test_outcome_is_derived_not_stored`
- `test_outcome.OutcomeTests.test_tie_breaks_by_earliest_sequence`

Every other test still passed against the mutant (the mutant
changes only who wins, nothing else — which is the point: the four
failures are exactly the tests that pin the invariant). The store
was then restored from `scratch/store.py.premutation` and verified
**byte-identical by SHA-256** (`scratch/store.py.sha256`), and the
full suite re-ran green: **74 tests, OK**.
