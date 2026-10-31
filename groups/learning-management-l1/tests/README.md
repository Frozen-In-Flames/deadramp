# Tests — Learning Management L1

Stdlib `unittest`, run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**137 tests, all passing.** Each module's header names the core
function / spec claim / control family its tests trace to.

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
