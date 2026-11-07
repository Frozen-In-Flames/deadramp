# Tests — Learning Management L1

Stdlib `unittest`, run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**170 tests, all passing** (137 founding + 33 from the final GAPS
batch unit, see the batch section at the end). Each module's header
names the core function / spec claim / control family its tests
trace to.

| Module | Traces to |
|---|---|
| `test_access.py` | Core 13 — permission matrix incl. the six new L1 actions; `organization_write` admin-only |
| `test_audit.py` | Core 14 — append-only audit, denied attempts recorded |
| `test_authorizations.py` | Core 4 — SF-182 records, decider ≠ creator (AC-5) |
| `test_catalog.py` | Core 2 — courses, content (standards enum incl. `html`), lesson plans |
| `test_competencies.py` | Core 6 — competency definitions & verbatim levels |
| `test_compliance.py` | Core 9 — derived compliance status (the signature invariant) |
| `test_continuing_ed.py` | Core 17 — CE records, `credit_text` verbatim, learner scope |
| `test_certificates.py` | Core 16 — certificate award records, exact key set, learner scope, no-score scan |
| `test_learners.py` | Core 1 — opaque learner registry, shape pinning |
| `test_main_cli.py` | Core 12 — CLI / demo users |
| `test_negative_control.py` | Core 9 — mutant-store negative control (below) |
| `test_organizations.py` | Core 15 — organization registry, learner `org_ref`, catalog visibility matrix |
| `test_plans.py` | Core 5 — IDP records |
| `test_progress.py` | Core 7 — progress records |
| `test_registrations.py` | Core 3 — events, registrations, derived seat counts |
| `test_reporting.py` | Core 11 — counts-only reporting (incl. the three new counts), search incl. organizations |
| `test_service.py` | Core 12 — HTTP surface incl. the three new route families, unknown-key refusal |
| `test_specs.py` | Spec integrity — census membership, taxonomy-verbatim (AST equality with the L2 extractor), literal claim table (TRAIN 0, CloudLCMS 1), verbatim evidence, census citations, near-miss pins |
| `test_statements.py` | Core 8 — LRS statement records, exact 8-key shape, no score field |
| `test_workflows_notifications.py` | Core 10 — workflow registry never executes; notification records |

## Negative control (mutation-verified)

Signature invariant: **compliance status is derived at read, never
stored** — an incomplete assignment past its due date reads
`overdue`, computed deterministically from the assignment, the due
date, the learner's progress records, and an explicit `as_of`.

Two layers:

1. `test_negative_control.py` — a `MutantLmsStore` whose
   `_derive_status` always returns `"current"`. The canonical
   expectations hold on the real store and fail on the mutant,
   asserted literally (`assertRaises(AssertionError)` on the
   mutant's outcomes).
2. **External mutation drill, performed in this tree** (record in
   `scratch/mutation-failures.txt`): the overdue branch of
   `_derive_status` in the real `src/lms/store.py` was patched to
   `return "current"`, the full suite run, then the store restored
   and verified SHA-256-identical
   (`8986a77e8f12b180affbfc2ee8d30904df1a77a6a46f7c7cf0971b69bcf03e5f`).
   Result: **137 ran, exactly 9 failed** — six in
   `test_compliance`, the negative control's canonical test, the
   reporting derived-status test, and the service full-flow test.
   After restoration: **137 ran, OK**.

One reconciliation during the build, recorded for honesty: the
content-standard enum's new value is the lowercase token `"html"`,
following the substrate's all-lowercase token convention
(`scorm_1_2`, `xapi`, `pdf`); the tests' first draft used the
display form `"HTML"` from the spec's prose list. The spec's
implementation-contract line was corrected to name the token, and
the tests pin both directions (`"html"` accepted, `"HTML"`
rejected, like `"SCORM_1_2"`).

## Final GAPS batch — Remainder Group 2

`test_gaps_batch.py` (33 tests) pins the batch extension surface in
`src/lms/extensions.py`: the authoring environment, course posting
workflow, and system integration engines as labeled reference
records; the portal presentation, CE renewal-cycle, and
certificate service surfaces as records with derived-at-read
values; the no-score/no-grade recursive key scan over every
extension surface; `ext_`-prefixed audit actions; denied writes
consuming no id. **Suite total: 170 tests, all passing** (137
before the batch unit).

Fresh negative controls for the new code (mutation-verified):

1. `TestNegativeControl` in `test_gaps_batch.py` — a
   `MutantCeExtensions` whose `_derive_ce_cycle_status` inverts
   the coverage branch (a cycle with a qualifying core CE record
   reads uncovered; an empty cycle reads `satisfied`). The
   canonical expectations hold on the real surface and fail on
   the mutant, asserted literally (`assertRaises(AssertionError)`
   on the mutant's outcomes). A second mutant,
   `MutantPortalExtensions`, ignores portal revisions in
   `_current_presentation`; the freshness expectation (latest
   revision wins) fails on it the same way.
2. **External mutation drill, performed in this tree** (record in
   `scratch/gaps-batch-mutation-failures.txt`): the coverage
   branch of `_derive_ce_cycle_status` in the real
   `src/lms/extensions.py` was patched from `if qualifying:` to
   `if not qualifying:`, the full suite run, then the module
   restored and verified SHA-256-identical
   (`0d9222842a12034c40fe644e1fc9e738fa2e247008f3103be3a42e338cf39f86`).
   Result: **170 ran, exactly 3 failed** — two in
   `TestContinuingEducationEngine` (derived status; out-of-period
   and undated records) and the negative control's canonical CE
   test. After restoration: **170 ran, OK**.
