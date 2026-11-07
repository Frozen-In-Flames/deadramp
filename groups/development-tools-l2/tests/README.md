# Tests — Development Tools L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

**Provenance:** this suite is Group 17's (Development Tools L1) test
suite, copied **byte-identical** (all 16 files, verified by SHA-256
comparison against `../../development-tools-l1/tests/` at delivery)
and run against this group's byte-identical reuse of Group 17's
implementation. The negative control and mutation drill below were
performed **fresh in this tree**.

## Run

```bash
cd groups/development-tools-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 66 tests
```

Status at delivery: **66 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/developer/viewer, `permissions_for()`, `can()`, `require()`, unknown role denied, developer lacks `audit_read` |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording mutations and denied attempts |
| `test_projects.py` | Core 1 project registry — creation shape/provenance, `prj-` ids, get/list, empty-name validation with no id consumed, viewer write denied, plain-string actor convention |
| `test_issues.py` | Core 2 issue tracking incl. lifecycle — `iss-` shape, unknown project, list filters, happy-path lifecycle, illegal/same-state/unknown transitions rejected with state unchanged |
| `test_reviews.py` | Core 3 code-review records — `rev-` shape, state transitions, merged/closed terminal, list filter. Records only |
| `test_builds.py` | Core 4 build records — `bld-` shape, default `succeeded`, all four statuses accepted, bad status rejected with no id consumed. Records only |
| `test_releases.py` | Core 5 release records — `rel-` shape, duplicate version in same project rejected, same version in different project allowed |
| `test_artifacts.py` | Core 6 artifact registry incl. checksum verify — sha256/size computed from str/bytes content, checksum-only registration, neither-given rejected, mismatched checksum+content rejected, `verify_artifact` true/false on tampered content, no content stored |
| `test_deployments.py` | Core 7 environment & deployment records — `env-`/`dep-` shapes, bad status rejected, unknown env/project/release/artifact → NotFoundError, list filters |
| `test_search.py` | Core 8 search — case-insensitive hits across all five families, no-hit empty lists, empty query → ValidationError, `search` action required |
| `test_store_validation.py` | SI-10 store validation — failed creates across types consume no ids, permission checked before validation/allocation, no-actor writes denied, wrong-typed inputs rejected |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (project → issue + lifecycle → review → build → release → artifact + verify → environment → deployment → search), viewer write 403 + denied audited, audit admin-only, 400/404 envelopes |
| `test_main_cli.py` | `python -m devtools serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `test_additions.py` | Remainder additions (unit `addition:development-tools-l2`, see `../ADDENDUM.md`) — spec integrity: sheet count/unit order, membership vs `remainder.json`, literal per-fork claim table (7 claims), verbatim evidence, census citations (5/5), zero-claim fork (Unqork) and 12 zero-claim families pinned, near-miss pins, Copado visual wording-artifact pin; substrate cases: one per addition fork against the unchanged core (Cloud.gov environment/deployment records, Copado build/release/deployment records + artifact verify, FGC landing-zone deployment, Unqork project/issue records incl. the lifecycle gate) |
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

Traceability to this group's claims: Core 9 is exercised against
LaunchDarkly's access_control claim (feature-level RBAC) and Core 10
against AutoRABIT's audit_logging claim ("immutable audit trails");
Core 4's records against LaunchDarkly's ci_pipeline claim. The
remaining Core functions are carried substrate (see UNION-SPEC.md's
core-boundary decision) and trace to the Moderate baseline families
(AC/IA/AU/SI/CM/SC) mapped there.

## Negative control

`test_negative_control.py` implements the contract's negative
control with two families:

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

VERIFIED fresh in this tree (2026-10-25). The lifecycle gate in
`DevToolsStore.set_issue_status` (`src/devtools/store.py`) — the
`if status not in allowed:` check against `ISSUE_TRANSITIONS` — was
patched so `set_issue_status` accepts any transition
(`if False and status not in allowed:`), the exact live counterpart
of the mutant in `test_negative_control.py`. The full suite was run:
**66 tests ran, 8 failed** (recorded in `scratch/mutation-run.txt`) —

- `test_issues.TestIssues.test_lifecycle_illegal_transitions_rejected_state_unchanged` (subtests `bad='open'`, `bad='resolved'`, `bad='bogus'`, `bad='merged'`, plus the follow-on in-progress check in the same test)
- `test_negative_control.TestNegativeControlLifecycle.test_closed_to_resolved_rejected_canonical`
- `test_negative_control.TestNegativeControlLifecycle.test_open_to_resolved_rejected_canonical_but_mutant_allows`
- `test_service.TestServiceAccessAndErrors.test_validation_400_and_not_found_404`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.pristine`; SHA-256
`36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`, byte-identical via `cmp`, and byte-identical
to Group 17's shipped `store.py`) and the suite re-run: **66 tests,
OK**. The suite catches this defect class; the negative control is
not decorative.

## Remainder additions — spec integrity and drill re-run

`test_additions.py` (12 tests) pins the appended spec sheets and
exercises one substrate case per addition fork; see its module
docstring and `../ADDENDUM.md`. Status after the additions:
**78 tests, OK**.

The group's signature mutation drill was **re-run in this tree**
for the additions (2026-10-31): the same lifecycle-gate patch as
above (`if status not in allowed:` → `if False and status not in
allowed:` in `DevToolsStore.set_issue_status`). The full suite
ran: **78 tests, 9 failed** (raw output in
`scratch/additions_mutation_run.txt`) — the original drill's 8
(the `test_issues` illegal-transition subtests, the two
`test_negative_control` canonicals, and
`test_service.TestServiceAccessAndErrors.test_validation_400_and_not_found_404`)
plus 1 from the new additions module,
`test_additions.TestAdditionSubstrateCases.test_unqork_zero_claim_fork_records_and_lifecycle_gate`,
whose direct assertion of the gate (open → resolved rejected,
state unchanged) trips on the mutant exactly as designed.
`store.py` was restored from the pre-mutation copy
(`scratch/store.py.premutation.additions`) and verified
SHA-256-identical to the shipped hash
(`36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0`);
the suite re-ran green: **78 tests, OK**.

## Smoke

A live smoke (`scratch/smoke.py`) drives the store and the HTTP
service end to end: project → issue → lifecycle to `resolved` →
review → build record → release → artifact with checksum verify
(original True, tampered False) → environment → deployment → search
hit; a viewer write attempt returns 403 over HTTP and the denial is
present in the audit log. Result at delivery: **SMOKE OK**.

## Dependency check

`scratch/verify_deps.py` parses every `.py` file under `src/` with
`ast` and asserts every imported top-level module is in
`sys.stdlib_module_names`. Result at delivery: imports found
`argparse, dataclasses, datetime, hashlib, http, json, os, ssl, sys,
threading, urllib`; third-party imports: none. **OK: stdlib only.**

## Final GAPS batch (2026-11-07)

The batch unit for this group's GAPS section adds
`tests/test_gaps_batch.py` (43 tests) pinning the extension
surface in `src/devtools/extensions.py`: pipeline definitions
and reported run records, toolchain registry records, artifact
storage backends as records + checksums with a read-time
placement summary, the feature-flag evaluation derivation
(bucketing rule recomputed independently in the test module,
targeting and kill-switch precedence, evaluation storing
nothing), experiment assignment under the same bucketing rule
with verbatim outcomes and exact-count summaries, rule sets /
quality profiles / reported analysis results with read-time
gate derivations, release plans with recorded stage states and
a derived plan view, and the eight labeled reference records
(`reference_stub: True`, `recorded_reference_only`; creating
one changes no core record set). The seven pre-existing core
modules are byte-identical to the shipped build (hashes
re-verified against the UNION-SPEC contract table at batch
build time); the extension module only reads core records and
appends to the core audit log. Status after the batch:
**121 tests, OK**.

**Fresh negative control (this batch): the kill-switch-blind
flag evaluation.** The load-bearing invariant of the flag
runtime is that a killed flag serves NO subject, whatever its
targeting or rollout says. The test subclasses
`DevToolsExtensions` and breaks the kill-switch seam
(`_kill_switch_active` returns `False` unconditionally),
sharing the recorded flag table so the seam is its only
difference. The canonical test asserts the three properties
the rest of the suite relies on: (1) the real implementation
evaluates a killed, targeted, 100%-rollout flag as
`served: False` with reason `kill_switch`; (2) the mutant
would NOT produce it — it serves the targeted subject with
reason `targeted`; and (3) treating the mutant outcome as the
expectation raises `AssertionError` literally. The mutant is
defined inside the test; production code on disk is untouched
by the test itself.

**Mutation drill (performed at batch build time).** The real
`extensions.py` was mutated so `_kill_switch_active` returns
`False` unconditionally, and the full suite was run:

| code under test | result |
| --- | --- |
| real implementation | 121 tests, all pass |
| kill-switch-blind mutant | exactly **2 failures**: `test_kill_switch_and_restore` (the canonical kill/restore behavior) and `test_kill_switch_ignoring_mutant_is_rejected` (the negative control itself, whose canonical expectation is produced by the now-mutated real implementation) |

Both failures sit on the kill-switch surface and nothing else
trips, which is the specificity the drill exists to prove: the
suite detects exactly the invariant the seam guards.
`extensions.py` was then restored from the pre-mutation copy
and verified byte-for-byte against its pre-drill SHA-256
(`a3b7598b6166a42cdd0dcf321f17e5d9a991ca3f46f3841a00c662bf6a0e734d`),
and the suite re-run green at 121 tests. Raw drill output is
at `scratch/gaps_mutation_run.txt`; the pre-mutation copy is
at `scratch/extensions.py.premutation`.

## Final GAPS batch — second unit: remainder addition (2026-11-07)

The batch's second unit in this group adds
`tests/test_gaps_batch_addition.py` (23 tests) pinning the
addition surface in `src/devtools/extensions_addition.py`:
application definition records for the no-code / low-code
platform entry (idx 578 — components held as inert data,
deep-copied at the boundary, versioned on revision;
`definition_only` and `built_here` / `run_here` /
`executed_here` / `rendered_here` all pinned), publication
records reported by the external platform (status vocabulary,
definition-revision snapshot, optional core-environment
binding), the read-time application view (stored definition
carries no count or status), the labeled document-generation
reference records for the SSP generation entry (idx 579 —
`reference_stub: True`, `generated_here: False`,
`document_held_here: False`; outcome labels verbatim; the
derived generation view), the core-unchanged pin (creating
addition records changes no core record set), RBAC denials
audited under the core log, mutations audited under the
`exta_` prefix, and the derived addition summary. All 8
pre-existing `src/devtools/` modules are byte-identical to
the shipped build plus the first batch unit (hashes
re-verified against `scratch/prebatch-addition-src.sha256`
at build time); the addition module only reads core records
and appends to the core audit log. Status after this unit:
**144 tests, OK**.

**Fresh negative control (this unit): the earliest-reading
latest-label seam.** The load-bearing invariant of both
derived views is that the current reported state is the
*latest* record reported: a publication recorded after
another supersedes it, and an outcome recorded after another
supersedes it. `LatestLabelNegativeControlTests` shares the
record tables with a subclass that breaks the seam
(`_latest_label` returns the earliest record's label). The
canonical test asserts the three properties the rest of the
suite relies on: (1) the real implementation derives the
latest publication status (`reported_failed` after
`reported_published` then `reported_failed`); (2) the mutant
would NOT produce it — it reports the superseded
`reported_published`; and (3) treating the mutant outcome as
the expectation raises `AssertionError` literally. The
mutant is defined inside the test; production code on disk
is untouched by the test itself.

**Mutation drill (performed at build time).** The real
`extensions_addition.py` was mutated so `_latest_label`
returns `records[0][key]` instead of `records[-1][key]`
(occurrence count asserted = 1 before replacing), and the
full suite was run:

| code under test | result |
| --- | --- |
| real implementation | 144 tests, all pass |
| earliest-reading mutant | exactly **3 failures**: `ApplicationPublicationTests.test_application_view_derives_and_stores_nothing`, `DocumentGenerationReferenceTests.test_view_derives_latest_outcome_and_stores_nothing`, and `LatestLabelNegativeControlTests.test_canonical_latest_publication_status` |

All three failures sit on the latest-label surface and
nothing else trips, which is the specificity the drill
exists to prove: the suite detects exactly the invariant
the seam guards. `extensions_addition.py` was then restored
from the pre-mutation copy and verified byte-for-byte
against its pre-drill SHA-256
(`416819c1cc9ee1d2b899e549b7d340a0335aa34ed01f0455e3a17c5e1d5f60b5`),
and the suite re-run green at 144 tests. Raw drill output
is at `scratch/gaps_addition_mutation_run.txt`; the
pre-mutation copy is at
`scratch/extensions_addition.py.premutation`.
