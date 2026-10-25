# Tests — Development Tools L1 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/development-tools-l1
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

VERIFIED by the build worker (2026-10-25). The lifecycle gate in
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
`scratch/store.py.sha256`, and byte-identical via `cmp`) and the
suite re-run: **66 tests, OK**. The suite catches this defect class;
the negative control is not decorative.

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
