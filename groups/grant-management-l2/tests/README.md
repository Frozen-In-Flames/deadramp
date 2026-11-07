# Tests — Grant Management L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/grant-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 93 tests
```

Status at delivery: **93 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 12 Access control — exact permission matrix, `require()`; audit_read admin-only |
| `test_programs.py` | 12 | 1 Grant programs — creation validation (float/bool/negative money, bad window), derived open status, stored record carries no status key, membership boundary, member management |
| `test_organizations.py` | 6 | 2 Applicant organizations — pinned record shape, duplicate refs, profile updates |
| `test_applications.py` | 11 | 3 Applications — money validation, form linkage, lifecycle transitions and their failure atomicity |
| `test_reviews_decisions.py` | 14 | 4 Reviews (verbatim, no score field anywhere), 5 Decisions & awards — AC-5 submitter/decider separation, approval/decline shape rules, the award cap (exactly-at-budget OK, 1 cent over rejected whole, two awards summing over rejected) |
| `test_reports.py` | 7 | 6 Post-award reports — derived pending/overdue/submitted, stored record carries no status key, double-submit rejected |
| `test_documents.py` | 6 | 7 Documents — checksum validation and normalization, signature events, double-sign rejected |
| `test_registries.py` | 5 | 8 Forms & workflows — definition validation; the workflow registry never executes (behavior pin + no execution entry point) |
| `test_communications.py` | 6 | 9 Messages, notifications, internal notes — notes stay internal for read-only members |
| `test_reporting.py` | 5 | 10 Search & summary — counts/sums computed from records; outsider search sees no program content |
| `test_service.py` | 6 | 11 REST API — live HTTP: 401/403/404/400 semantics, the full grant flow over HTTP, denied attempts audited with `:denied` |
| `test_audit.py` | 4 | 13 Audit log — mutation recording, entry shape, JSONL persistence round-trip, no mutation API |
| `test_main_cli.py` | 1 | CLI — `python -m grants serve` subprocess answers `/health` |
| `test_negative_control.py` | 3 | Negative control (below) |
| `grants_helpers.py` | — | Canonical fixture: program by bob, erin added as staff member (the canonical decider), ORG-100 applicant; outsider dave in no program |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is the **award cap**: awards recorded against a program never
exceed its budget. The mutant is a `GrantsStore` subclass
(`MutantGrantsStore`) whose `_check_award_cap` does nothing. The
tests assert the canonical expectation (an over-cap decision is
rejected), that the implementation matches it across multiple
awards, and — via a literal `assertRaises(AssertionError)` — that
the canonical expectation rejects the mutant's outcome (the mutant
records an award of budget + 1 cent).

## Mutation verification

VERIFIED by the coordinator for this group: `_check_award_cap` in
the real `src/grants/store.py` was patched to a no-op and the suite
was run against the patched implementation.

- Patched run: **93 ran, exactly 4 failed**:
  - `test_negative_control.TestNegativeControlAwardCap.test_canonical_expectation_rejects_over_cap`
  - `test_negative_control.TestNegativeControlAwardCap.test_implementation_matches_canonical_across_awards`
  - `test_reviews_decisions.TestAwardCap.test_one_cent_over_is_rejected_whole`
  - `test_reviews_decisions.TestAwardCap.test_two_awards_summing_over_budget_second_rejected`
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`1e340e6a…`, recorded in
  `scratch/store.py.sha256`); the suite is green again (93/93).
  Raw drill output is in `scratch/mutation-run.txt`.

The failing set is exactly the cap-dependent set: the
exactly-at-budget test still passes under the mutant (an at-cap
award is legal with or without the check), and the separation-of-
duties and derivation tests are untouched by this mutation, as
expected.

## Interpretation notes

- Program open status and report status are derived at read: the
  tests pin this twice over, once through the public views at
  different `now` values and once by asserting the raw stored
  records (`store._programs`, `store._reports`) carry no `status`
  key at all.
- Application lifecycle status is event-driven, not date-driven,
  so it *is* stored — the distinction is deliberate and stated in
  the store's module docstring.
- `decide_application` returns `{"decision": ..., "application":
  ...}` plus `"award"` on approvals only; a decline carries no
  award key and `amount_cents: None` on the decision.
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.

## Final GAPS batch — Singleton 45 extension tests

`test_gaps_batch.py` (42 tests) pins the batch extension surface
in `src/grants/extensions.py` (`GrantsExtensions`, a wrapper around
the core store; every core module is byte-identical to its shipped
hash — `store.py` still `1e340e6a…`). Coverage per GAPS.md entry:
portal configuration records (`rendered_here` / `served_here`
False; one per program; role and membership boundaries), form
layout records validated against the core form definition's field
names (unknown field and duplicate placement rejected whole, no id
consumed), document vault records (`content_held` False) with
verify-by-content derivations, disbursement records (float/bool/
zero amounts rejected; summary totals derived at read), dashboard
definitions whose runs derive panel values and store nothing,
export records with derived count manifests, delivery receipts
(`reference_transport: True`, `delivered_here` False), the
deterministic presence match (per-application evidence, creation
order preserved — no ranking), eligibility criteria checks derived
at read and never stored, the merit-scoring records form (rules
held as data with `applied_here` False; reported outcomes verbatim
and the core application record byte-identical before/after),
reconciliation views with variances derived at read in exact
integer cents (the stored record holds only the reported figure),
closeout records gated on derived readiness, and the two
stub-engine surfaces (workflow run references and signing
references, `reference_stub: True`, pinned to change no core
record — a signing reference leaves the core document unsigned).
A recursive key scan pins the founding no-score invariant over the
whole extension surface: no score-, rating-, grade-, or
rank-shaped key in any returned value. Cross-cutting pins:
`ext_`-prefixed audit actions on the core log, denied writes
recorded with a `:denied` suffix, and no id consumed by a failed
operation.

### Batch mutation verification — fresh negative control

VERIFIED by the coordinator (2026-11-07). The batch's fresh
negative control targets the disbursement cap in the NEW code:
`GrantsExtensions._check_disbursement_cap`
(`src/grants/extensions.py`) — its single comparison line
`if disbursed + amount_cents > award["amount_cents"]:` (occurs
exactly once in the file, count asserted before patching) — was
patched to `if False:`, so recorded disbursements could exceed an
award's recorded amount. The full suite was run: **135 tests ran,
exactly 4 failed**:

- `test_gaps_batch.TestDisbursements.test_one_cent_over_cap_rejected_whole`
- `test_gaps_batch.TestDisbursements.test_rejected_disbursement_consumes_no_id`
- `test_gaps_batch.TestDisbursementCapNegativeControl.test_canonical_expectation_rejects_over_cap`
- `test_gaps_batch.TestDisbursementCapNegativeControl.test_implementation_matches_canonical_across_disbursements`

`extensions.py` was then restored from the pre-mutation copy
(`scratch/extensions.py.premutation`; SHA-256
`611bb0db3c558361fed64b369f772b041c8ebde0ec13d49dde91b1804aa04d12`,
verified identical after restore against
`scratch/extensions.py.sha256`) and the suite re-run: **135 tests,
OK**. The raw failure list is in `scratch/gaps_mutation_run.txt`.
No core test failed under the mutant — the disbursement cap is new
code and its load-bearing tests are the batch's own, as the batch
pattern requires. The founding award-cap drill above remains this
tree's core control, unchanged.

Full suite status after the batch: **135 tests, OK** (93 at
delivery + 42 batch tests). Core modules byte-identical to their
shipped hashes; `extensions.py` is the only new module in
`src/grants/`.
