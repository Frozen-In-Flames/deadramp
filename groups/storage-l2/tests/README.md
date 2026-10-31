# Tests — Storage L2 singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**79 tests, all passing** (Python 3 standard library `unittest`
only). Each test module's header names the core function, spec
claim, or control family it traces to.

| Module | Covers |
|---|---|
| `test_access.py` | Role/permission matrix (AC family) |
| `test_registries.py` | Organization, retention-policy & collection registries: pinned shapes, ref uniqueness, policy immutability, integer retention days (SI-10) |
| `test_messages.py` | Message archive records: metadata-only pinned shape (recursive no-content scan), per-collection ref uniqueness, custody linkage guards, no-id-on-failure |
| `test_retention.py` | **The signature invariant**: the derivation seam, derived-at-read state (never stored), derived boundary, exact-boundary eligibility, the disposition gate (refuses inside retention, allows at/after, refuses double), per-policy derivation |
| `test_discovery.py` | Discovery records: scope filters, computed result sets, no free-text query field on the shape |
| `test_supervision.py` | Supervision review records: lifecycle transitions, terminal `reviewed`, outcome validation |
| `test_enforcement.py` | Enforcement action records; an `extend_retention` record provably does not change the derivation |
| `test_retrievals.py` | Retrieval & export records: modes/destinations, completion lifecycle |
| `test_custody.py` | Key custody records: shape holds no key material, one-active-per-collection invariant, retire & replace |
| `test_integrations.py` | Integration registry: records only, no execution surface, deactivate lifecycle |
| `test_reporting.py` | Search (literal, metadata-only) & summary: counts only, retention counts follow the clock through the same seam, recursive no-score key scan |
| `test_audit.py` | Append-only audit log; mutations recorded, failures not; `audit_read` admin-only; JSONL persistence |
| `test_service.py` | REST API over real HTTP: full flow through the retention gate, float/bool rejected (400), auth failures (401/403), exactly 3 denied attempts audited |
| `test_main_cli.py` | CLI argument handling and demo-user wiring |
| `test_specs.py` | Spec integrity: membership == census unit {F1304222071}, recorded fields match `forks.json`, taxonomy == the 11 own-description families, evidence verbatim, census citations verify, checked absences hold at token level |
| `test_negative_control.py` | The mutation-verified negative control (below) |

## Negative control — mutation-verified

The signature invariant is the retention derivation: a message's
retention state is computed at read by the single seam
`_derive_retention_state` in `src/storage/store.py`, and a
disposition may be recorded only when the derived state is
`disposition_eligible`. An oracle that passes whether or not
retention has expired is testing that code ran, not that
retention is enforced — so the invariant is verified two ways:

1. **In-tree mutant** (`test_negative_control.py`): the canonical
   gate expectation is asserted against a run where the seam is
   swapped for a mutant reporting every non-disposed message as
   `retained` forever (the gate never opens). The test asserts
   the canonical check fails against the mutant, and a second arm
   asserts the gate stays shut before the boundary on the real
   store.
2. **External drill** (performed on this tree, recorded in
   `scratch/mutation-run.txt`): the eligibility comparison in the
   real `src/storage/store.py` was patched to `if False:`, the
   full suite re-run, and the file then restored.

**Drill result: exactly 9 tests did not pass out of 79 (7
failures, 2 errors):**

- `test_retention.SeamTests.test_seam_states`
- `test_retention.RetentionViewTests.test_state_is_derived_at_read_and_never_stored`
- `test_retention.RetentionViewTests.test_exact_boundary_is_eligible`
- `test_retention.RetentionViewTests.test_list_filter_by_derived_state`
- `test_retention.DispositionGateTests.test_disposition_at_and_after_boundary` (error — its fixture path itself records a disposition on an eligible message; under the mutant the gate's `ValidationError` escapes as an error rather than a failed assertion)
- `test_retention.DispositionGateTests.test_double_disposition_is_refused` (error — same fixture shape)
- `test_reporting.ReportingTests.test_summary_retention_counts_follow_the_clock`
- `test_service.ServiceTests.test_full_flow_with_retention_gate`
- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`

Every other test still passed against the mutant — the mutant
changes only whether retention expires, nothing else, which is
the point: the nine are exactly the tests that pin the invariant.
The store was then restored from `scratch/store.py.premutation`
and verified **byte-identical by SHA-256**
(`scratch/store.py.sha256`), and the full suite re-ran green:
**79 tests, OK**.
