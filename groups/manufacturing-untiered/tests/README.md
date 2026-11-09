# Tests — Manufacturing, untiered (DeadRamp Phase 2, Untiered Set 26)

Run everything from this directory:

    cd groups/manufacturing-untiered
    PYTHONPATH=src python3 -m unittest discover -s tests

`manufacturing_helpers.py` builds a fresh store wired to an
in-memory audit log, with one actor per role — alice (admin),
bob (operator), carol (viewer) — and the shared fixtures (one
organization, intent and decision builders).

47 tests, fully green.

## Layout

- `test_access.py` — the roles/permissions matrix (core function
  7): admin, operator, viewer; unknown roles/users denied; the
  store enforces roles for User actors.
- `test_audit.py` — the audit log (core function 8): append-only
  entries with actor/action/target; entries returned as copies;
  JSONL persistence round-trips; no update/delete API.
- `test_intents.py` — organizations and intent records (core
  functions 1 and 2): organization references unique; the intent
  statement stored verbatim; author references cannot be email
  addresses or carry whitespace; intent status is derived at
  read through the `_derive_intent_status` seam (`open`, then
  `transformed` once a decision cites the intent) and the stored
  record provably has no `status` key; status list filter;
  viewer writes denied.
- `test_decisions.py` — decision records and the basis guard
  (core function 3): a decision records its basis; empty or
  missing basis refused and consumes no id; unknown basis intent
  refused; another organization's intent refused; duplicate
  basis refused; decider references cannot be email addresses;
  multi-intent bases record; viewer writes denied.
- `test_shapes.py` — pinned record shapes: exact key sets for
  all three record types (the stored intent set proves no stored
  `status`; the intent view adds exactly the derived `status`);
  a recursive scan over a fully populated store's public surface
  proves no forbidden key part exists anywhere (score, grade,
  rank, rating, rate, email, ssn, password, secret, salary,
  wage, price, fee, amount, cost, budget); the summary is counts
  only.
- `test_negative_control.py` — the mutation-verified negative
  control (below).
- `test_service.py` — the REST API over real HTTP (core function
  6): health is public; missing headers, unknown users, and
  mismatched roles are 401; the full flow exercises the
  decision-basis guard end to end (a basisless decision is a
  400, and the next good decision is still `dec-1`) and the
  derived intent status; viewer writes are 403 and audited with
  a `:denied` suffix; the audit endpoint requires `audit_read`;
  404/405 mapping.
- `test_main_cli.py` — the CLI entry point: demo-user wiring; no
  command returns 2.
- `test_specs.py` — spec integrity: membership exactly the census
  unit `untiered:Manufacturing` ({FR2632054516}); tier null on
  the sheet (`cmmc_tier` None, `fedramp_impact_level` "Unknown");
  recorded vendor/product/status match forks.json; the census
  proposed Manufacturing as a new category for this fork; the
  sheet's description is byte-identical to the source
  description; the claim table equals the expected table (4
  claims) under the set's own 4-family taxonomy; every claim's
  evidence sentence appears in the description, and the evidence
  sentences are exactly the description's two sentences; both
  census citations verify and both serve as claim evidence (this
  set's direction — see UNION-SPEC.md); the `certified_services`
  record field is empty and was never matched; the
  checked-absence tokens are absent from the description at
  token level.

## Negative control — the decision-basis-guard drill

The signature invariant is the decision-basis guard: a decision
record may not be recorded without at least one basis intent
that exists and belongs to the same organization, because the
function this set claims is the transformation of engineering
intent into decisions, and a decision resting on no intent
transforms nothing. An oracle that passes whether or not the
guard enforces would be testing that code ran, not that the
guard holds. The drill mutates the guard seam in the real
`src/manufacturing/store.py`:

    def _check_decision_basis(intents_by_id, org_id, basis_intent_ids):
        return None  # MUTANT (drill): decision-basis guard disabled

(the body that validates the basis is replaced with a no-op),
then the full suite is re-run. Result: exactly 6 failures, all
guard-dependent —

- `test_decisions.TestDecisions.test_cross_organization_basis_is_refused`
- `test_decisions.TestDecisions.test_duplicate_basis_is_refused`
- `test_decisions.TestDecisions.test_empty_basis_is_refused_and_consumes_no_id`
- `test_decisions.TestDecisions.test_unknown_basis_intent_is_refused`
- `test_negative_control.TestNegativeControl.test_canonical_guard_refuses_basisless_decision`
- `test_service.TestService.test_full_flow`

No other test moved: the guard's neighbours (verbatim statements,
opaque references, role enforcement, the derivation seam) do not
depend on the seam's refusal and correctly kept passing. Raw
drill output: `scratch/mutation-failures.txt`.

After the drill, `store.py` is restored byte-identical
(SHA-256 `9e3e6c7494d913c77e548864f9dfb724afeda70e4ae469527be7cb8e28f0656d`,
verified with `sha256sum -c` against `scratch/store.py.sha256`)
and the suite is fully green again. `test_negative_control.py`
also carries the drill's in-tree form: the same mutant applied by
monkeypatch, with the canonical check asserted to fail against
it — plus the discriminating other arm (a decision resting on
exactly one valid basis intent IS recorded on the real store, so
the invariant is a floor of one, not a ban).

## Final GAPS batch coverage (Set 26 section, 2026-11-08)

- `test_gaps_batch.py` — the batch extension surface
  (`manufacturing.extensions.ManufacturingExtensions`): the
  section's 1 open entry (idx 958, the engineering-intent
  transformation engine including the manufacturing-intelligence
  engine entire) closed as a labeled reference implementation
  (re-judged from its drafted build-extension disposition;
  grounds in `../BATCH.md`). Transformation request records
  under the core decision-basis guard's records form (empty /
  duplicate / unknown / cross-organization bases refused with
  no id consumed; requester refs cannot be email addresses;
  viewer writes denied with no id consumed); outcome records
  holding the external engine's reported label verbatim
  (off-vocabulary labels refused; citing a foreign core decision
  refused; an outcome creates no core decision); request views
  deriving `outcome_count` and `latest_outcome_label` at read
  with the stored request's exact key set pinned free of derived
  keys; the counts-only summary; a full flow leaving every core
  record byte-identical; the no-content signature discipline
  (no `**kwargs` anywhere, no content-shaped parameter, smuggled
  `content=` / `statement=` kwargs raise `TypeError`); and the
  recursive scans — no tier / baseline / impact / equivalence
  key, no score or money key, and no float value anywhere on the
  surface (tier null, preserved).

### Negative control — the latest-outcome drill (fresh, batch)

The batch's fresh mutation-verified negative control targets
the extension's latest-outcome seam,
`ManufacturingExtensions._latest_outcome_label`: a request
view's `latest_outcome_label` must be the label of the most
recently recorded outcome, derived at read and stored nowhere.
The in-suite form (`TestNegativeControlLatestOutcome`) is
three-legged: the canonical view reads the latest outcome; an
earliest-reading mutant subclass reads the earliest; treating
the mutant's outcome as the canonical expectation raises
`AssertionError`. The live drill patched the seam's return line
in the real `src/manufacturing/extensions.py`
(`outcomes[-1]` → `outcomes[0]`, occurrence count asserted = 1
before patching) and re-ran the full suite: exactly **3
failures** of 73, all in `test_gaps_batch.py` —

- `test_gaps_batch.TestDerivedViewsAndSummary.test_view_derives_count_and_latest_outcome`
- `test_gaps_batch.TestNegativeControlLatestOutcome.test_canonical_view_uses_latest_outcome`
- `test_gaps_batch.TestNegativeControlLatestOutcome.test_seam_directly`

— with all 47 founding tests still passing. Raw drill output:
`scratch/gaps_batch_mutation_run.txt`. After the drill,
`extensions.py` was restored from
`scratch/extensions.py.premutation`, SHA-256 verified identical
(`058d48a5…`), and the suite re-ran fully green (73 tests).
Suite count: 47 before → 73 after.
