# Tests — Research L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/research-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 97 tests
```

Status at delivery: **85 tests, OK**.
Status after the remainder additions (`addition:research-l2`):
**97 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 10 Access control — exact permission matrix for the research actions, `require()` denials; audit_read admin-only |
| `test_commons.py` | 17 | 1 Commons registry — creation validation (bad kind, duplicate name, failed creation consumes no id), event-driven lifecycle and its illegal transitions, membership boundary (outsider denied, admin reaches without membership), pinned stored shape |
| `test_organizations.py` | 6 | 2 Organizations — pinned record shape, duplicate refs, profile updates |
| `test_workspaces.py` | 5 | 3 Workspaces — pinned shape, create/get/list inside a commons, outsider denied |
| `test_datasets.py` | 9 | 4 Datasets — pinned exact key set (no field can hold content), checksum validation and normalization, size validation, tier validation, verify-by-content true/false |
| `test_access_requests.py` | 9 | 5 Access requests — controlled-only rule (open dataset rejected), duration validation (floats/bools/strings rejected whole), withdraw lifecycle |
| `test_decisions_grants.py` | 10 | 6 Decisions (AC-5 requester/decider separation with no state change on denial; non-pending decision rejected; decline mints nothing), 7 Grants — expiry = start + duration, derivation scheduled/active/expired, revocation beats expiry, stored record carries no `status` key, derived-status list filter |
| `test_reporting.py` | 6 | 8 Search & summary — substring search scoping (outsider sees no commons content); summary counts computed from records, grants recounted by derived status at two clocks |
| `test_service.py` | 7 | 9 REST API — live HTTP: 401/403/404/400 semantics, the full sharing flow over HTTP including grant reads at two `?now=` values, denied attempts audited with `:denied` |
| `test_audit.py` | 5 | 11 Audit log — mutation recording, entry shape, JSONL persistence round-trip, no mutation API |
| `test_main_cli.py` | 1 | CLI — `python -m research serve` subprocess answers `/health` |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_additions.py` | 12 | Remainder additions (`addition:research-l2`, see `../ADDENDUM.md`) — spec integrity: sheet count/order, membership vs `remainder.json`, literal claim table (2 claims, both `data_sharing`), zero-claim forks/families pinned, near-miss pins, census citations; substrate cases: Terra sharing flow + grant derivation at three clocks, ROSALIND tier gate + revocation, Ipsos pinned dataset shape, Seven Bridges workspace/tier listing + outsider boundary, Wellspring organization shape + summary counts |
| `research_helpers.py` | — | Canonical fixture: commons `gen3-commons` by bob, erin added as staff member (the canonical decider — requests are bob's, and the decider is never the requester), ORG-100 organization; outsider dave in no commons; fixed clock anchors (T0, window, expiry) |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is **grant status derivation**: a grant reads `active` only while
unrevoked, unexpired, and started, and that status is derived at
read, never stored. The mutant is a `ResearchStore` subclass
(`MutantResearchStore`) whose `_derive_grant_status` always
returns `"active"`. The tests assert the canonical expectations
(an expired grant reads `expired`; a revoked grant reads
`revoked`), and — via literal `assertRaises(AssertionError)` —
that the canonical expectations reject the mutant's outcomes (the
mutant reports both grants as `active`).

## Mutation verification

VERIFIED by the coordinator for this group:
`_derive_grant_status` in the real `src/research/store.py` was
patched to return `"active"` unconditionally and the suite was
run against the patched implementation.

- Patched run: **85 ran, exactly 7 failed**:
  - `test_decisions_grants.TestGrantDerivation.test_status_is_derived_from_the_read_clock`
  - `test_decisions_grants.TestGrantDerivation.test_revocation_beats_expiry`
  - `test_decisions_grants.TestGrantDerivation.test_list_grants_status_filter_uses_derived_status`
  - `test_negative_control.TestNegativeControlGrantDerivation.test_canonical_expired_grant_reads_expired`
  - `test_negative_control.TestNegativeControlGrantDerivation.test_canonical_revoked_grant_reads_revoked`
  - `test_reporting.TestCommonsSummary.test_summary_counts_computed_from_records`
  - `test_service.TestServiceFlow.test_full_sharing_flow_over_http`
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`ff43a9ac…`, recorded in
  `scratch/store.py.sha256`); the suite is green again (85/85).
  Raw drill output is in `scratch/mutation-run.txt`.

The failing set is exactly the derivation-dependent set: the
separation-of-duties, open-dataset-gate, and shape-pinning tests
are untouched by this mutation (they guard different seams), and
the boundary test (a read at exactly `expires_at` still derives
`active`, because expiry is `moment > expires_at` per the
contract) is a canonical-expectation test that passes under both
implementations — the mutant agrees with the contract at that one
instant by construction.

## Mutation verification — additions re-run (2026-10-31)

The remainder additions left the core unchanged, so the same
drill was re-run in this tree against the enlarged suite:
`_derive_grant_status` in the real `src/research/store.py` was
patched to return `"active"` unconditionally and the full suite
was run.

- Patched run: **97 ran, exactly 9 failed** — the original
  drill's 7 above, plus 2 from the new additions module:
  - `test_additions.TestAdditionSubstrateCases.test_terra_sharing_flow_and_grant_derivation`
  - `test_additions.TestAdditionSubstrateCases.test_rosalind_tier_gate_and_revocation`
- `store.py` was then restored from
  `scratch/store.py.premutation.additions` and verified
  **SHA-256-identical** (`ff43a9ac…`, the shipped hash in
  `scratch/store.py.sha256`); the suite is green again (97/97).
  Raw drill output is in `scratch/additions_mutation_run.txt`.

The two additions failures are the derivation-dependent cases by
design: Terra's flow reads the grant at three clocks and recounts
the summary after expiry, and ROSALIND's case reads a revoked
grant inside its window — both report `active` under the mutant
and are rejected by the canonical expectations.

## Interpretation notes

- Grant status is derived at read: the tests pin this twice over,
  once through the public views at different `now` values and once
  by asserting the raw stored records (`store._grants`) carry no
  `status` key at all and match the pinned key set exactly.
- Commons lifecycle status and request lifecycle status are
  event-driven, not date-driven, so they *are* stored — the
  distinction is deliberate and stated in the store's module
  docstring.
- `decide_access_request` returns `{"decision": ..., "request":
  ...}` plus `"grant"` (the grant view, with derived status) on
  approvals only; a decline carries no grant key and mints no
  grant record.
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.
- Derivation boundary, per the contract text: a grant is `expired`
  only when the read moment is strictly after `expires_at`, so a
  read at exactly `expires_at` derives `active`. The tests assert
  the contract as written rather than a rounded version of it.

## Final GAPS batch additions (2026-11-07)

| File | Tests | Covers |
|---|---:|---|
| `test_gaps_batch.py` | 34 | Final GAPS batch unit (see `../BATCH.md`) — per-entry pins for idx 521–530: runtime configuration records (derived parameter count, stored record carries no count key); ingestion pipeline definitions + reported runs (a run leaves the core dataset record byte-identical; bad state/count rejected whole, consuming no id); harmonization mapping definitions + verbatim reported outcomes; indexing reference records (`reference_stub: True`, core literal search results unchanged); query definitions as text-free structure (`TypeError` on a `query_text` keyword) + reported result counts; cohort definitions with no subject field (exact key set; `TypeError` on a `subject_refs` keyword) + reported membership counts; federation peer/exchange records (`reference_transport: True`); delivery records with current state derived at read (stored record carries no state key) and the two-way grant pins (grant minting changes no delivery; an enforcement decision changes no grant and no delivery state); enforcement decision records + `delivery_access_view` deriving the core grant's status at three clocks; identity reference records (`identity_provider: False`); a recursive forbidden-key scan over every extension record, view, and summary; and the batch's fresh negative control (below) |

Status after the final GAPS batch unit: **131 tests, OK**.

## Negative control — batch (delivery state derivation)

**`TestDeliveryDerivationNegativeControl`** in
`test_gaps_batch.py` — the batch's fresh invariant is **delivery
current-state derivation**: a delivery's current state is its
latest recorded reported-* label, derived at read by the single
seam `ResearchExtensions._current_delivery_label`, never stored
(the stored delivery record carries no state key — pinned). The
mutant is a `ResearchExtensions` subclass whose seam returns the
EARLIEST recorded label. The tests assert the canonical
expectation (a prepared → dispatched → received delivery reads
`reported_received`), that the mutant reads `reported_prepared`
instead, and — via literal `assertRaises(AssertionError)` — that
the canonical expectation rejects the mutant's outcome.

## Mutation verification — batch drill (2026-11-07)

VERIFIED by the coordinator for this batch unit:
`_current_delivery_label` in the real `src/research/extensions.py`
was patched to `return states[0]["state_label"]` (earliest wins)
and the full suite was run against the patched implementation.

- Patched run: **131 ran, exactly 2 failed**:
  - `test_gaps_batch.TestDeliveries.test_current_state_derived_from_latest`
  - `test_gaps_batch.TestDeliveryDerivationNegativeControl.test_canonical_reads_latest_state`
- `extensions.py` was then restored from
  `scratch/extensions.py.premutation` and verified
  **SHA-256-identical** (`9c82de73…`, recorded in
  `scratch/extensions.py.sha256`); the suite is green again
  (131/131). Raw drill output is in
  `scratch/gaps_batch_mutation_run.txt`.

The failing set is exactly the derivation-dependent set: the
mutant-agreement legs of the control pass under both
implementations by construction, and the delivery tests that
record a single state (the grant-minting and enforcement pins)
cannot distinguish earliest from latest — they guard different
seams (record immutability across core grant and decision
events), as the core drill's boundary test did for the grant
derivation.

## Final GAPS batch additions — remainder unit (2026-11-07)

| File | Tests | Covers |
|---|---:|---|
| `test_gaps_batch_addition.py` | 32 | Final GAPS batch remainder unit (see `../BATCH-ADDITION.md`) — per-entry pins for idx 580–588: pipeline definitions bound to a core dataset/workspace (derived step count, stored record carries no count key; duplicate/foreign bindings rejected whole, consuming no id) + run requests and verbatim reported outcomes (an outcome leaves the core dataset record byte-identical); allocation requests (zero/float/bool/string amounts rejected whole) + reported outcomes, summary totals pinned as sums of recorded values only; analysis requests + results held as opaque references only (`TypeError` on a `result_text` keyword; a result leaves the core dataset byte-identical); disclosures + agreements (stored record carries no state key) with current state derived at read and the summary recounting by derived state; labeled reference records for environments (`provisioned_here`/`executed_here` False), BioBank samples (exact key set keyed by opaque sample ref only; `TypeError` on `diagnosis`/`subject_ref` keywords) + verbatim monitoring outcomes, knowledge-graph nodes/edges (unknown endpoint rejected; `traversed_here` False), surveys + reported response counts (`TypeError` on a responses-payload keyword), document-generation requests (output as opaque ref), signing requests (exact key set; `TypeError` on a `signature_value` keyword), and integration references (`connected_here` False); outsider/viewer write denials (guard-denied attempts audited as `add_*:denied`); a recursive forbidden-key scan over every addition record, view, and summary; and the addition's fresh negative control (below) |

Status after the final GAPS batch remainder unit: **163 tests, OK**.

## Negative control — batch addition (agreement state derivation)

**`TestAgreementDerivationNegativeControl`** in
`test_gaps_batch_addition.py` — the addition's fresh invariant is
**agreement current-state derivation**: an agreement's current
state is its latest recorded reported-* label, derived at read
by the single seam `ResearchAdditions._current_agreement_label`,
never stored (the stored agreement record carries no state
key — pinned). The mutant is a `ResearchAdditions` subclass
whose seam returns the EARLIEST recorded label. The tests assert
the canonical expectation (a proposed → negotiated → executed
agreement reads `reported_executed`), that the mutant reads
`reported_proposed` instead, and — via literal
`assertRaises(AssertionError)` — that the canonical expectation
rejects the mutant's outcome.

## Mutation verification — batch addition drill (2026-11-07)

VERIFIED by the coordinator for this batch unit:
`_current_agreement_label` in the real `src/research/addition.py`
was patched to `return states[0]["state_label"]` (earliest wins)
and the full suite was run against the patched implementation.

- Patched run: **163 ran, exactly 3 failed**:
  - `test_gaps_batch_addition.TestTechTransfer.test_current_state_derived_from_latest`
  - `test_gaps_batch_addition.TestTechTransfer.test_summary_recounts_by_derived_current_state`
  - `test_gaps_batch_addition.TestAgreementDerivationNegativeControl.test_canonical_reads_latest_state`
- `addition.py` was then restored from
  `scratch/addition.py.premutation` and verified
  **SHA-256-identical** (`e52e5b44…`, recorded in
  `scratch/addition.py.sha256`); the suite is green again
  (163/163). Raw drill output is in
  `scratch/gaps_batch_addition_mutation_run.txt`.

The failing set is exactly the derivation-dependent set: the
mutant-agreement legs of the control pass under both
implementations by construction, and the addition tests that
record a single agreement state (the shape and bad-label cases)
cannot distinguish earliest from latest — they guard different
seams. No core test and no first-unit (`test_gaps_batch.py`)
test failed under the mutation: the seam is the addition's own,
in the addition's own module.
