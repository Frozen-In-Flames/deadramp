# Tests — Development Tools, untiered set

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

**Provenance:** this suite is the founding group's (Development
Tools L2, itself Group 17's suite) test suite, carried
**byte-identical** — every carried file SHA-256-matches its founding
counterpart — **minus** `test_additions.py`, which pins a different
census unit (the L2 remainder additions) and is not carried. The new
`test_specs.py` is this set's own. The negative control and mutation
drill below were performed **fresh in this tree**.

## Run

```bash
cd groups/development-tools-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 74 tests
```

Status at delivery: **74 tests, OK** against the implementation in
`../src/` (66 carried core tests + 8 spec tests). (Run exactly as
above: helpers are imported as a top-level module from the tests
directory and `tests/__init__.py` is empty by design, so
package-mode discovery with `-t .` is not the supported entry point
for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/developer/viewer, `permissions_for()`, `can()`, `require()`, unknown role denied, developer lacks `audit_read` |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording mutations and denied attempts |
| `test_projects.py` | Core 1 project registry — creation shape/provenance, `prj-` ids, get/list, empty-name validation with no id consumed, viewer write denied, plain-string actor convention |
| `test_issues.py` | Core 2 issue tracking incl. lifecycle gate — `iss-` shape, unknown project, list filters, happy-path lifecycle, illegal/same-state/unknown transitions rejected with state unchanged |
| `test_reviews.py` | Core 3 code-review records — `rev-` shape, state transitions, merged/closed terminal, list filter. Records only |
| `test_builds.py` | Core 4 build records — `bld-` shape, default `succeeded`, all four statuses accepted, bad status rejected with no id consumed. Records only |
| `test_releases.py` | Core 5 release records — `rel-` shape, duplicate version in same project rejected, same version in different project allowed |
| `test_artifacts.py` | Core 6 artifact registry incl. checksum verify — sha256/size computed from str/bytes content, checksum-only registration, neither-given rejected, mismatched checksum+content rejected, `verify_artifact` true/false on tampered content, no content stored |
| `test_deployments.py` | Core 7 environment & deployment records — `env-`/`dep-` shapes, bad status rejected, unknown env/project/release/artifact → NotFoundError, list filters |
| `test_search.py` | Core 8 search — case-insensitive hits across all five families, no-hit empty lists, empty query → ValidationError, `search` action required |
| `test_store_validation.py` | Store validation (SI-10 in the founding contract's terms; at tier null, input-validation substrate) — failed creates across types consume no ids, permission checked before validation/allocation, no-actor writes denied, wrong-typed inputs rejected |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (project → issue + lifecycle → review → build → release → artifact + verify → environment → deployment → search), viewer write 403 + denied audited, audit admin-only, 400/404 envelopes |
| `test_main_cli.py` | `python -m devtools serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `test_specs.py` | **This set's spec integrity (new)** — exactly 7 sheets; sheet fork_id set == remainder.json unit `untiered:Development Tools`; tier discipline (every `cmmc_tier` None, every `fedramp_impact_level` `"Unknown"`); every claim's evidence verbatim in its description (under the founding `\r`→space normalization, stated in the test); every sheet's category; literal totals (14 claims, zero-claim set exactly {FR2701457600}); the exact per-fork claim table; and the exclusion-pass pin (no claim's evidence carries scope-exclusion phrasing) |
| `devtools_helpers.py` | Shared fixtures: demo users (ADMIN/DEVELOPER/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a DevToolsStore + AuditLog + one project (created by ADMIN) |

## Coverage table

| Core function | Test files |
|---|---|
| 1. Project registry | `test_projects.py`, `test_service.py`, `test_main_cli.py` |
| 2. Issue tracking w/ lifecycle | `test_issues.py`, `test_negative_control.py`, `test_service.py` |
| 3. Code-review records | `test_reviews.py`, `test_service.py` |
| 4. Build records | `test_builds.py`, `test_service.py` |
| 5. Release records | `test_releases.py`, `test_service.py` |
| 6. Artifact registry w/ checksums | `test_artifacts.py`, `test_negative_control.py`, `test_service.py` |
| 7. Environment & deployment records | `test_deployments.py`, `test_service.py` |
| 8. Search | `test_search.py`, `test_service.py` |
| 9. RBAC | `test_access.py`, `test_projects.py`, `test_search.py`, `test_store_validation.py`, `test_service.py` |
| 10. Audit log | `test_audit.py`, `test_service.py` |

Traceability to this set's claims: Core 2's lifecycle gate is
exercised against Linear's `issue_tracking` claim; Core 3's records
against Cursor's and KineticCode's `code_review` claims; Core 4's
records against Harness's `ci_pipeline` claim; Core 9 against
KineticCode's `access_control` claim; Core 10 against KineticCode's
and Moderniza's `audit_logging` claims. The remaining Core
functions are carried substrate (see UNION-SPEC.md's core-boundary
decision), pinned by the carried suite and by `test_specs.py`'s
membership and tier-discipline pins.

## Negative control

`test_negative_control.py` implements the contract's negative
control with two families (carried byte-identical from the founding
suite):

(a) **Lifecycle-gate tests** — a `DevToolsStore` subclass
(`MutantDevToolsStore`) whose `set_issue_status` accepts any
transition. The traced claim is that **issue status transitions are
lifecycle-only**: `open -> resolved` must be rejected and the state
must stay `open`, and `closed -> resolved` must be rejected. For each
canonical case the test asserts the canonical expectation (from the
real implementation), that the mutant would NOT produce that
expectation, and — via a literal `assertRaises(AssertionError)` —
that treating the mutant's outcome as the expected outcome fails.

(b) **Checksum-integrity tests** — `verify_artifact` is False on
tampered content (an always-True verify mutant is rejected the same
three-part way), and registering an artifact with a checksum and
content that differ is rejected with nothing stored.

## Mutation verification

VERIFIED fresh in this tree (2026-10-31). The lifecycle gate in
`DevToolsStore.set_issue_status` (`src/devtools/store.py`) — the
`if status not in allowed:` check against `ISSUE_TRANSITIONS` — was
patched so `set_issue_status` accepts any transition
(`if False and status not in allowed:`), the exact live counterpart
of the mutant in `test_negative_control.py`. The full suite was run:
**74 tests ran, 8 failed** (recorded in `scratch/mutation_run.txt`) —
the founding drill's identical failing set:

- `test_issues.TestIssues.test_lifecycle_illegal_transitions_rejected_state_unchanged` (subtests `bad='open'`, `bad='resolved'`, `bad='bogus'`, `bad='merged'`, plus the follow-on in-progress check in the same test)
- `test_negative_control.TestNegativeControlLifecycle.test_closed_to_resolved_rejected_canonical`
- `test_negative_control.TestNegativeControlLifecycle.test_open_to_resolved_rejected_canonical_but_mutant_allows`
- `test_service.TestServiceAccessAndErrors.test_validation_400_and_not_found_404`

No spec test failed under the mutant: `test_specs.py` pins the spec
sheets, not store behavior, exactly as designed — the drill's target
is the gate, and the gate's tests are the ones that trip.

`store.py` was then restored from the pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`, byte-identical via `cmp` to the founding
group's shipped `store.py`) and the suite re-run: **74 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.

## Smoke

A live smoke (`scratch/smoke.py`, carried from the founding group)
drives the store and the HTTP service end to end: project → issue →
lifecycle to `resolved` → review → build record → release → artifact
with checksum verify (original True, tampered False) → environment →
deployment → search hit; a viewer write attempt returns 403 over HTTP
and the denial is present in the audit log. Result at delivery:
**SMOKE OK**.

## Dependency check

`scratch/verify_deps.py` (carried from the founding group) parses
every `.py` file under `src/` with `ast` and asserts every imported
top-level module is in `sys.stdlib_module_names`. Result at
delivery: imports found `argparse, dataclasses, datetime, hashlib,
http, json, os, ssl, sys, threading, urllib`; third-party imports:
none. **OK: stdlib only.**

## Final GAPS batch — Untiered Set 6 unit (2026-11-07)

`test_gaps_batch.py` (34 tests, new) pins the extension surface in
`src/devtools/extensions.py` (`DevToolsExtensions`, wrapping the
core store) for the 7 open entries of this set's GAPS.md section
(inventory idx 796–802; per-entry dispositions in `../BATCH.md`):

| File | Covers |
|---|---|
| `test_gaps_batch.py` | idx 796 AI engines (reference form after re-judgment — stub labels, verbatim outcomes, view derives latest); idx 797 workspaces (declaration + session records, view derives latest reported status, stored record carries no status); idx 798 conversion jobs (five recorded stages as data, digest validation, view derives per-stage latest + overall); idx 799 governance gating (gate checks bound to same-project core subjects, pinned to change no core record; promotions with derived current state); idx 801 governance policies (rules as data, sequence/threshold validation, cross-project policy binding rejected); idx 800 detection (reference as drafted — scan + reported finding records, stub labels); idx 802 support cases (channel labels, `reference_transport`, state derived from event records, no message field); cross-cutting (tier-null recursive key scan over every extension record family and derived view; extension writes change no core record set; failed operations consume no ids; viewer write denied and audited `project_write:denied`); negative control (below) |

Run (updated count):

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 108 tests
```

Status after the batch: **108 tests, OK** (74 carried + 34 batch).
The 7 core modules are byte-identical to the shipped build
(SHA-256 re-verified against the group README's table before and
after). Dependency check re-run: stdlib only (the new module adds
`copy`). The founding `scratch/smoke.py` still passes (SMOKE OK),
and an in-process smoke of the extension surface (policy →
conversion job + stage → workspace + session → support case, all
mutations audited under `ext_` actions) passed at delivery.

### Batch negative control and mutation verification (fresh)

`TestNegativeControlConversionDerivation` implements the batch's
negative control in three-part form. The traced claim is that
**a conversion stage's current reported status is its LATEST
recorded outcome**: after `reported_in_progress` then
`reported_completed` are recorded for a stage, the job view reads
`reported_completed`. The mutant
(`EarliestOutcomeMutantExtensions`) derives from the earliest
outcome instead. The test asserts the canonical expectation from
the real implementation, that the mutant would NOT produce it
(it reads `reported_in_progress`), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails.

VERIFIED fresh in this tree (2026-11-07). The derivation seam
`DevToolsExtensions._derive_conversion_stage` in
`src/devtools/extensions.py` — the line
`return outcomes[-1]["status_label"]` — was patched to
`return outcomes[0]["status_label"]`, the exact live counterpart
of the mutant. The full suite was run: **108 tests ran, exactly
3 failed** (recorded in `scratch/gaps_mutation_run.txt`):

- `test_gaps_batch.TestConversionJobs.test_job_view_derives_latest_stage_status`
- `test_gaps_batch.TestNegativeControlConversionDerivation.test_control_passes`
- `test_gaps_batch.TestNegativeControlConversionDerivation.test_earliest_outcome_mutant_is_rejected` (its canonical leg asserts the literal canonical value against the real implementation, so it trips under the live mutation as designed)

`extensions.py` was then restored from the pre-mutation copy
(`scratch/extensions.py.premutation`; SHA-256
`483d234232f04dfc14c989f0045c4d5bdb7c93a22b1876dff65aeecc521d2bfe`,
verified identical to the pre-mutation hash in
`scratch/extensions.py.sha256`) and the suite re-run: **108
tests, OK**. The suite catches this defect class; the negative
control is not decorative.
