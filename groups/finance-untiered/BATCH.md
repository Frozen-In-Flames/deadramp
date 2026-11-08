# Final GAPS batch — Untiered Set 24, Finance

Unit: the 2 OPEN entries of the GAPS.md section
**`## Untiered Set 24 — Finance (1 fork, tier null)`** (the set's
1 fork is Emburse / Emburse Enterprise, FR2633058235). Built
2026-11-07 under `../../gaps-batch/DECISION.md` (the 2026-11-07
ratified triage) and `../../PLATFORM-LAYER.md`. Entry count
verified against both sources before building: GAPS.md's section
lists exactly 2 `- [] open` entries and
`../../gaps-batch/inventory.json` assigns exactly idx 948–949 as
open to this section — **no discrepancy**. The section's third
entry, idx 950 ("Platform layer", triage `rescope-platform`), was
already closed `re-scoped` under `../../PLATFORM-LAYER.md` at the
batch foundation; it is not part of this unit, is untouched, and
is named here so the section's count reconciles (3 entries: 2
open → closed by this unit, 1 already re-scoped).

**Naming note (premise checked, corrected):** the build brief
described this as the *second* batch unit in this directory,
landing as `extensions_addition.py` / `BATCH-ADDITION.md` beside
an existing first unit's `extensions.py` / `BATCH.md`. That
premise does not hold for this directory: no `extensions.py`,
`test_gaps_batch.py`, or `BATCH.md` existed here (the directory's
only prior commit is the founding Phase 2 build, 307f6e7), so
this is the **first** batch unit for the set and it lands with
first-unit naming, exactly as `DECISION.md`'s build pattern
specifies ("Each unit writes BATCH.md in its group directory").
All pre-existing modules are byte-identical either way.

All extension code is one new module, `src/finance/extensions.py`
(`FinanceExtensions`, wrapping the untouched core store, audit
actions prefixed `ext_`); every existing module is byte-identical
(SHA-256 verified against the pre-build record in
`scratch/prebatch-src.sha256`; `store.py` still `f905061d…`, the
founding group's shipped hash). Tests:
`tests/test_gaps_batch.py` (47 tests; suite 209 → 256, all
passing). Per-entry dispositions below use the exact entry texts
from GAPS.md / `gaps-batch/inventory.json` (idx 948–949). The
disposition column is the closure token the parent records in
GAPS.md.

**Tier discipline is unchanged and pinned on the new surface:**
tier stays null — no baseline is asserted, no CMMC equivalence is
drawn, and a recursive scan over every extension record and view
finds no tier / baseline / impact / equivalence key (and no float
value anywhere). **Finance doctrine is unchanged:** money is
integer cents only (booleans and floats rejected at every
boundary), money never moves here (the reimbursement record
carries `paid_here` / `settled_here`: False), totals derive at
read over this surface's own recorded figures and state their
basis, and the expense layer is a separate surface from the
core's budgets / accruals / program summary — a full expense flow
leaves every core record byte-identical (pinned by test), and
nothing here merges into the tiered builds' ledger, CPM, or
federal-system-of-record surfaces.

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 948 | Expense reporting, approval & reimbursement workflow engine (this fork's described function entire, named by no taxonomy family — registered in its own name) | stub-engine | **built** (**re-judged**, grounds below) | Expense report records (`exp-`: bound to a core participant of the same program — either kind files expenses; lines held as exactly `{category, amount_cents}` with positive integer cents and unique categories, deep-copied at the boundary, so no line shape can carry a note, a receipt image, or any content) running the core's own workflow shape: `draft → submitted → approved / denied`, `approved → reimbursed` via a reimbursement record, `draft / submitted / denied → void`. **Separation of duties** exactly as the core's `decide_access`: the decider is never the report's creator (pinned). Submit/void are restricted to creator, program owner, or platform admin, mirroring the core's void rule. The stored report carries **no total**; `get_expense_report` / list views derive `total_cents` at read from the recorded lines (pinned). Reimbursement records (`rei-`: amount, participant, and period taken from the report; `paid_here` / `settled_here`: False — a record, after the fact, that money moved on external rails, the core's disbursement-record doctrine). `expense_summary` derives counts and totals by status plus `reimbursed_cents` at read over this surface's own records only, stating its basis. |
| 949 | Travel & expense policy enforcement engine | build-extension | **built** (as drafted) | Policy records (`pol-`: declared rules held as data, `definition_only: True`; a rule is exactly `{kind, category, limit_cents}` over `category_line_cap` / `report_total_cap`, limit a non-negative integer-cents value, (kind, category) unique per policy) plus compliance evaluations derived at read: `evaluate_expense_report` computes violations from the policy's recorded rules and the report's recorded lines through the `_exceeds` seam (strictly greater exceeds; exactly-at-cap complies, mirroring the earned-cap boundary). The evaluation is a view, never stored (repeat evaluations are equal and change no record, pinned); it flags and blocks nothing — `blocked_here: False`, `paid_here: False` — because no payment exists in this build to block. |

## Re-judgment (DECISION.md qualification 1)

**idx 948: stub-engine → built.** The drafted triage was
pattern-based: the entry sits in the `workflow-execution`
cluster, whose reason reads "engine over external systems". On a
close reading of this set's own `UNION-SPEC.md`, the gap is
specified not as an external automation engine but as "expense
records running a submit → review → approve → administer
workflow with reimbursement recording" — a records state machine
over records this substrate holds. That shape is the carried
core's own Core function 8 (workflow & approvals with separation
of duties, implemented for wage-access records), and the one
external act the entry implies — the reimbursement payment —
already has the founding form in Core function 3: a disbursement
*record* stating that money moved on external rails, executed
nowhere here. Nothing in the built surface executes a step
against an external system, runs an automation, or moves money;
every transition is a human actor's recorded act on a held
record, RBAC- and membership-gated, audited, and fail-closed on
audit write. Shipping the surface labeled `reference_stub` would
misstate it in the other direction: the workflow is genuinely
implemented, in the same form the founding build implements its
own. The build is identical if the parent prefers to token it
`reference`; the grounds are recorded here either way.

No other re-judgment: idx 949 closes with its drafted
disposition, and idx 950 was already closed in writing at the
foundation and is not re-opened.

## Negative control

Fresh, for this surface: the policy-comparison seam
(`FinanceExtensions._exceeds`). The canonical rule: a recorded
line (or report total) strictly greater than a recorded cap is a
violation; exactly-at-cap complies. The in-suite three-leg
control in `tests/test_gaps_batch.py`
(`TestPolicyEvaluationNegativeControl`): the canonical evaluation
flags a meals line 1 cent over its 5000¢ cap (1 violation, not
compliant); a violation-blind mutant subclass sharing the record
tables (seam returns False unconditionally) reads the same report
compliant with no violations; treating the mutant's outcome as
the canonical expectation raises `AssertionError`. Live drill
performed 2026-11-07 (recorded in `tests/README.md`, log in
`scratch/gaps_batch_mutation_run.txt`): patching the seam's
return line to `return False` (occurrence count asserted = 1
before patching) produced exactly **4 failures** out of 256 — the
three violation-expecting evaluation tests and the control's
canonical leg — with all 209 founding tests still passing; the
module was restored from `scratch/extensions.py.premutation`,
SHA-256 verified identical (`b59a76aa…`), and the suite re-run
green (256 tests, OK).

## What is NOT covered (named, not closed silently)

- **No reimbursement is executed.** No money is paid, settled,
  or moved on any rail; reimbursement records state that an
  approved report was reimbursed elsewhere, and say so on their
  face (`paid_here` / `settled_here`: False).
- **No receipt or document content exists here.** Expense lines
  are a category label and an integer-cents amount — exactly two
  keys, pinned. There is no field for a receipt, an image, a
  note, or any attachment, and none was added.
- **Policy evaluation advises; it does not enforce against a
  payment.** It derives flags over recorded rules and lines at
  read. It does not block a submission, a decision, or a
  reimbursement record, and it evaluates no rule kind beyond the
  two recorded cap kinds.
- **The founding group's extended tail stands where it was
  registered** (instant disbursement execution / payment rails,
  travel booking execution engines, financial wellness delivery
  tools, streaming / real-time reporting pipelines): registered
  under the founding group, not re-registered or absorbed here.
- **PLATFORM-LAYER.md decisions 1–6 are untouched** by this
  unit: no identity provider, no validated cryptography, no
  retention enforcement, no session layer, and no hosting or
  multi-tenancy claim was built or implied. The section's own
  platform-layer entry (idx 950) stays closed `re-scoped` on
  that decision, exactly as the foundation left it.
- **HTTP exposure** of the extension surface was out of scope
  for the batch pattern (extensions land in `src/` with tests);
  the service layer is untouched.
