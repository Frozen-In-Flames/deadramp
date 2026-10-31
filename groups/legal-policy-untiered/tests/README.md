# Tests — Legal & Policy, untiered set

Run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**103 tests, all passing.** The suite is the founding Legal &
Policy build's suite **carried with the code** (94 tests — the
founding group's own suite minus its 12-test additions module,
which pins the founding group's tiered addition unit and is not
carried) plus this set's spec tests (9 tests in `test_specs.py`).
The carried tests were not weakened: their assertions are the
founding build's, and the only edits are first-line docstring
labels in `legalpol_helpers.py`, which name this set where the
founding file named the founding group. The founding
`test_negative_control.py` keeps its "Group 49" trace lines
verbatim — the drill it names is the founding drill, re-run
here.

| File | Tests | Covers |
|---|---:|---|
| test_access.py | 7 | role validation, permission matrix (incl. auditor-free shape), default-deny, read/write derivation |
| test_agencies_workspaces.py | 15 | agency registry, membership uniqueness/revoke, workspace kinds and per-agency uniqueness, scoping rules |
| test_sessions_executions.py | 14 | session/execution lifecycles, sandbox kinds, expiry boundary, **single-use rule**, execution outcome shape |
| test_library_searches.py | 11 | library source kinds/statuses/refresh cadence, saved-search digest-only storage, query-text leak scan |
| test_documents.py | 10 | document metadata record, checksum shape, verify-by-content, content-leak scan |
| test_usage_exports.py | 9 | usage quantities (positive int only), export manifests, export immutability |
| test_reports_search.py | 7 | report shape and determinism, search scoping and ordering, unknown-token behaviour |
| test_privacy.py | 4 | entity key-set pins, no score/rating/status-of-merit field, stored shapes |
| test_audit.py | 7 | append-only log, denied-attempt recording, admin-gated audit read |
| test_service.py | 6 | full flow, HTTP-free service behaviour, error mapping |
| test_main_cli.py | 1 | CLI entrypoint behaviour |
| test_negative_control.py | 3 | **mutation drill (below)** |
| test_specs.py | 9 | this set's spec sheets: exactly 3, membership exact against census unit `untiered:Legal & Policy`, tier discipline on every sheet ("Unknown" / null), registry fields vs `forks.json`, business categories as recorded in the source, descriptions verbatim vs the census record (Casepoint's "\r" preserved), the literal zero-claim table, the certified-services exclusion, census citations 4/4 |

## Negative control (mutation-verified, re-run in this tree)

**Drill (the founding group's signature drill, re-run verbatim
in this tree):** in `src/legalpol/store.py`, the
`_check_sandbox_unused` seam — the single chokepoint the store
calls before storing any execution record — is patched to a
no-op body:

```python
        return None  # MUTANT (mutation drill)
```

(the seam body replaced verbatim, compile-checked before the
run). Then the full suite runs. **Exactly 4 tests fail** — the
same 4 the founding drill fails at founding scope (the founding
suite's fifth drill failure lives in its additions module,
which is not carried here):

1. `test_negative_control.TestNegativeControlSandboxSingleUse.test_canonical_expectation_rejects_second_execution`
2. `test_negative_control.TestNegativeControlSandboxSingleUse.test_mutant_also_breaks_derived_consumption_semantics`
3. `test_sessions_executions.TestExecutions.test_single_use_rule`
4. `test_service.TestFullFlow.test_flow`

The two canonical negative-control tests assert the second
execution is rejected and the derived consumption read-out
flips; the two positive-path tests carry the same contract from
the other side. Nothing else fails (103 ran, 99 passed — no
spec test failed), and the green suite with the mutant removed
proves the checks are executable assertions against a working
store rather than wishes.

**Evidence:** raw run output in `scratch/mutation_run.txt`
(gitignored); the premutation file is `scratch/store.py.
premutation` and its recorded digest `scratch/store.py.sha256`.
**Restore verified:** after the drill, `store.py` was restored
from the premutation copy and its SHA-256 re-computed as
`7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`
— identical to the founding build's shipped `store.py` — and
the full suite re-ran green (103/103). This is the same drill
the founding build and its additions pass recorded; a future
change that retires the single-use rule will have to retire
these tests in the open.

**Live smoke** (`tests/smoke.py`, shipped alongside): boots the
real HTTP server on an ephemeral port, creates an agency,
member, workspace, library source, saved search, and document,
runs one sandbox execution (201) and a second one against the
same session, which must come back **400** with the single-use
error, then checks the report. Smoke passed in this tree.

## Substrate accounting (SHA-256)

`src/legalpol/` was carried whole from
`groups/legal-policy-l2/src/legalpol/`:

| Module | This set | Founding build | Verdict |
|---|---|---|---|
| `__init__.py` | `26c0911e…` | `5470ed79…` | differs — docstring first line only, re-anchored to name this untiered set (the Research untiered set's precedent) |
| `__main__.py` | `717ac1a3…` | `717ac1a3…` | byte-identical |
| `access.py` | `a4af66f1…` | `a4af66f1…` | byte-identical |
| `audit.py` | `7de3b7dd…` | `7de3b7dd…` | byte-identical |
| `errors.py` | `4dc62495…` | `4dc62495…` | byte-identical |
| `service.py` | `dfb4b986…` | `dfb4b986…` | byte-identical |
| `store.py` | `7030f9fd…` | `7030f9fd…` | byte-identical (its module docstring still names the founding group — carried verbatim as part of the identical file) |

6 of 7 modules byte-identical; the seventh differs by one
docstring line. Full digests were computed at build time and are
reproducible with `sha256sum src/legalpol/*.py` in both group
directories.
