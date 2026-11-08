# Final GAPS batch — second unit: Remainder Addition — Travel Management L2

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Travel Management L2 (+1 fork)`**
(the +1 fork is mLINQS Hosting Service, F1610037949, added to
this group by the remainder census; its spec sheet's ADDENDUM
§5 registered these gaps). Dispositions follow
`../../gaps-batch/DECISION.md`; platform-layer closures follow
`../../PLATFORM-LAYER.md`.

**Entry-count verification:** no discrepancy. GAPS.md's section
lists exactly 2 `- [ ] open` entries, and
`gaps-batch/inventory.json` assigns exactly idx 681–682 to this
section, both drafted `build-extension` — matching the brief.

Everything landed as ONE new module,
`src/travel/extensions_addition.py` (`TravelExtensionsAddition`,
wrapping the core `TravelStore`), with audit actions prefixed
`exta_`. All 8 pre-existing modules — the 7 core modules and
the first batch unit's `extensions.py` — are byte-identical
(SHA-256 verified against the pre-build record in
`scratch/prebatch-addition-src.sha256`; `store.py` still
`a4098ea6…`, first unit's `extensions.py` still `76e1924b…`).
No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py`. Suite: **148 → 177**, all
passing.

Category discipline holds on the whole surface: booking never
happens here and nothing is booked, moved, paid, or processed;
money is integer cents end to end (bool and float rejected at
the boundary, no id consumed); traveler and employee data is
never held — the case binds a core traveler by opaque id only,
origins and destinations are labels, and signature pins prove
no `employee_name=`, `document_number=`, or `daily_rate=` can
enter any shape; determinations derive at read and are never
stored.

## Per-entry disposition

### idx 681 — built (build-extension, as drafted)

> Employee relocation management & processing engine: the relocation lifecycle (a permanent move, distinct from a trip; the fork's headline function — no registered gap names it)

Built as records, in the substrate's own lifecycle form:

- `create_relocation_case` (`rlc-`): a case record bound to a
  core organization and a core traveler (the traveler's org
  must match; the traveler id is copied from the core record,
  never a name), holding origin/destination labels, a move
  date, and an estimated cost in integer cents. The entry's
  own distinction is structural and pinned by test: a case is
  **never bound to a core trip authorization** — a relocation
  is a permanent move, not a trip. `moved_here` /
  `relocated_here` / `processed_here: False`,
  `state: recorded_case_only`.
- Lifecycle: `submit_relocation_case` and
  `decide_relocation_case` (`rlcd-` decision records) — the
  core's event-driven lifecycle carried to this surface, with
  separation of duties: the decider is never the case's
  creator, pinned by test.
- `record_relocation_event` (`rle-`): processing milestones
  over a kind vocabulary (household_goods, temporary_quarters,
  travel, storage, closeout, other) with outcome labels and
  amounts stored **verbatim as reported**; events require an
  approved case, as expense reports require an approved
  authorization in the core. Nothing is processed here —
  processing happened elsewhere and is reported to this build.
- `relocation_case_view`: derives event count, latest reported
  outcome, the reported event total (a sum of amounts reported
  by others, stated as such), and the case's entitlement
  totals at read; the stored case record carries none of those
  keys, pinned by test. A test also pins the core traveler
  record byte-identical across a full case flow.

### idx 682 — built (build-extension, as drafted)

> Relocation policy & entitlement rules automation: automation of the federal relocation policy corpus the fork names in its own words (recorded as distinct from per-diem computation, which remains an absence — the fork automates relocation policy without naming any per-diem computation)

Built as rule definitions as data plus a deterministic
entitlement evaluation derived at read — the policy-evaluation
form the batch brief names for this category (a deterministic
derivation over the substrate's own recorded figures and
rules-as-data, with computed figures stating their basis):

- `register_policy_rule` (`rlr-`): a rule record naming the
  corpus it was recorded under — `corpus_label` over
  {`ftr`, `jtr`, `dssr`, `6fam`, `other`}, exactly the corpora
  the fork names in its own words ("automates FTR, JTR, DSSR,
  and 6FAM CONUS/OCONUS relocation policy", ADDENDUM sentence
  4) — plus an entitlement kind and a cap in integer cents.
  The rule is parameters, never the corpus: `definition_only:
  True`, `executed_here: False`, `corpus_text_held: False` —
  no field shape can hold regulation text (a smuggled
  `regulation_text=` raises TypeError, pinned).
- `record_entitlement_claim` (`rln-`): a claim against an
  approved case under a recorded rule of the same
  organization, holding the claimed figure **verbatim**. The
  claim record's key set is pinned: it carries **no
  determination** — no allowed or excess figure exists on any
  stored record.
- `entitlement_evaluation`: derived at read, stored nowhere.
  Per rule, the case's claimed total is summed from its claim
  records and the determination is derived through the seam
  `_derive_entitlement` (allowed = claimed bounded by the
  recorded cap; excess = claimed above the cap). The view
  states its basis on its face
  (`evaluation_basis: recorded_claims_against_recorded_rule_caps`,
  `computed_here: True` for the derivation itself) — every
  figure in it comes from records on this surface, nothing
  from any external system.
- **The per-diem bound is structural, as the entry's own text
  records it:** per-diem computation remains an absence. No
  rate, no day count, and no rate-times-days shape exists on
  this surface in any field (a smuggled `daily_rate=` raises
  TypeError; a recursive key scan pins no per-diem or rate key
  on any record or view), and `per_diem_computed_here` is
  False on every policy shape.

Grounds for `built` over `reference`: the "automation" here
never leaves the substrate — rules are recorded definitions
and the evaluation is a derivation over those definitions and
the case's own recorded claims, the same shape as this group's
voucher-cap and disbursement-cap derivations over recorded
figures. Nothing executes against the federal corpus or any
external system; what a reference token would add (an external
engine's reported outcomes) is not what this entry names — it
names the application of recorded policy to individual moves,
which is the derivation built here.

## Re-judgments

None. Both entries land at their drafted `build-extension`
disposition. Expected closure arithmetic for the parent:
**2 entries closed — 2 built, 0 reference, no token
overrides.**

## Negative control (fresh, mutation-verified)

Seam: `_derive_entitlement` in
`src/travel/extensions_addition.py` — a case's allowed
entitlement is the claimed figure bounded by the recorded rule
cap. In-suite three-leg control in
`TestEntitlementCapNegativeControl` (canonical derivation caps
a 450,000¢ claim at the recorded 400,000¢ cap with 50,000¢
excess / cap-blind mutant subclass allows the claim in full /
mutant-as-expectation fails via `assertRaises`), plus a live
drill on the real file: the seam's line
(`allowed_cents = min(claimed_cents, cap_cents)` → `allowed_cents
= claimed_cents`, occurrence count asserted = 1) → 177 ran,
**exactly 3 failures**, all in the new module (the canonical
negative-control leg, the evaluation-derivation test, the
case-view totals test). Restored from
`scratch/extensions_addition.py.premutation`, SHA-256 verified
identical (`a72a9d56…` — see
`scratch/extensions_addition.py.sha256`), suite re-ran green.
Recorded in `tests/README.md`; raw output in
`scratch/gaps_addition_mutation_run.txt`.

## Honesty notes

- Nothing on this surface books, moves, relocates, ships,
  pays, or processes anything; no regulation text is held; no
  per-diem is computed; every stored figure is either a
  definition's recorded parameter or a value reported verbatim
  by the people and systems that did the work, and every
  derived figure is computed at read from those records with
  its basis stated.
- Not covered (stays open in its own name, not closed by this
  unit): the relocation processing itself (carriers, household
  goods shipment, quarters provision — work performed on
  people and property, not records), the federal policy corpus
  itself, and per-diem computation, which remains the recorded
  absence the ADDENDUM states.
