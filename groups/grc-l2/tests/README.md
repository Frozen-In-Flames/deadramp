# Tests — GRC L2 build (Group 33)

Stdlib `unittest` only. Every test docstring names the core function /
spec claim / control family it traces to.

## Run

```bash
cd groups/grc-l2
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **118 tests, OK** against the implementation in
`../src/`, verified by the build worker's own run (2026-10-25).
After the remainder additions (unit `addition:grc-l2`, see
`../ADDENDUM.md`): **132 tests, OK**, re-verified on the final tree
by the additions build (2026-10-31).
(Run exactly as above: helpers are imported as a top-level module
from the tests directory and `tests/__init__.py` is empty by design,
so package-mode discovery with `-t .` is not the supported entry
point for this group.)

## Layout

| File | Covers (Core) |
|---|---|
| `test_access.py` | 9 RBAC — exact permission matrix for admin/member/viewer (12 actions; admin = all 12, member = 7, viewer = read only), `permissions_for()`, `can()`, `require()`, unknown role/action/user denied |
| `test_frameworks.py` | 1 Framework & control catalog registry — seed catalog has exactly 21 controls with pinned shape, `CONTROL_IDS`/`control_by_id`, seeded store registry (framework record + controls, seeding writes no audit), framework/control registration, duplicate + validation + 404 paths, member denied `manage_frameworks` |
| `test_systems.py` | 2 Governed-system registry — records keyed by opaque caller-supplied refs, free-text name as label only, duplicate/empty rejected, 404, viewer read-only |
| `test_indicators.py` | 3 Indicator registry — definitions linked to controls (unknown control rejected, duplicate rejected), recorded results with indicator/system/status-verbatim/timestamp-verbatim/recorded-by, default UTC timestamp, unknown indicator/system consumes no result id, list filters, viewer may not record |
| `test_evidence.py` | 4 Evidence registry — metadata record + SHA-256 of supplied content + byte size + control/system links, **verify-by-content (original True, tampered False, trailing-newline False)**, bytes/str equivalence, link validation consumes no id, review sets the recorded validation status verbatim (admin-only; the filing member may not review), verify never changes the recorded status |
| `test_findings.py` | 5 Finding / remediation records — creation shape, severity recorded verbatim, no score/rating/band/derived key on the record, the exact `FINDING_TRANSITIONS` map, every allowed transition passes, a 20-pair forbidden set denied with status unchanged, canonical open → in_progress → remediated → validated → closed path, `accepted_risk` requires a recorded rationale, and the **derivation**: current before and on the due date, overdue after it, not overdue once remediated/validated/closed or risk-accepted, and the stored record shown to carry no derived status key (derived_status appears only on as-of read copies) |
| `test_assessments.py` | 6 Assessment & authorization records — assessment shape with result recorded verbatim, unknown system/framework consumes no id, the exact `AUTH_TRANSITIONS` map, legal path + history growth, denied/expired reopen paths, 10 illegal transitions denied with status unchanged, authorization management is admin-only |
| `test_posture.py` | 7 Posture reporting — empty-store shape with every bucket present at zero, counts by framework/system/status, open + overdue counts via the read-time derivation (as_of moves the overdue count), verbatim severity buckets, indicator-results and evidence summaries, and a recursive assertion that no key anywhere mentions score/rating/grade/percent; posture writes no audit entry |
| `test_service.py` | 8 REST API — live HTTP server on an ephemeral port: `/health`, 401 unknown user / role mismatch / missing headers, 404 and 400 JSON `{error}` shapes, 403s for viewer posting, member framework registration, member evidence review, member authorization management, `audit_read` admin-only over HTTP, **denied attempts audited with `:denied`**, and a full flow (catalog → framework/control → system → indicator → result → evidence + verify → finding + derived status → illegal transition 400 → assessment → authorization → posture) |
| `test_main_cli.py` | `python -m grc serve` subprocess with demo users alice/bob/carol answering `/health`, `/systems`, `/posture` and `/audit`, role mismatch → 401, no-subcommand → help + exit 2 |
| `test_additions.py` | Remainder additions (unit `addition:grc-l2`) — spec integrity for the 5 appended sheets (count/order, membership vs `remainder.json`, the literal per-fork claim table, verbatim evidence, census citations, the pinned zero-claim families, near-miss pins, the Kovr wording artifact, the retired-absence claimant sets) plus one substrate case per addition fork against the unchanged core, with posture recursively asserted score-free |
| `test_negative_control.py` | Negative control (below) |
| `test_audit.py` | 10 Audit log — entry keys (AU-3), actor normalization, append-only surface (no update/delete API, `entries()` returns copies), JSONL persistence + reload, the store recording each mutation action (`framework_create`, `control_create`, `system_create`, `indicator_create`, `indicator_result_record`, `evidence_create`, `evidence_review`, `finding_create`, `finding_transition`, `assessment_create`, `authorization_create`, `authorization_transition`) incl. the transition `details` payload, reads and failed ops writing nothing |
| `grc_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, MEMBER=bob/member, VIEWER=carol/viewer), `make_store()` building a GrcStore + AuditLog + one governed system (`SYS-001`) + one indicator (`KSI-1` → IA-2), plus `fresh_store()`, `make_system()`, `make_indicator()`, `make_finding()` |
| `store.py.premutation` | Pre-mutation copy of `../src/grc/store.py` used by the mutation drill below (SHA-256 recorded there) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a status-derivation function whose overdue branch **never fires** —
it returns the stored lifecycle status unconditionally, whatever the
due date and as-of date. The traced claim, named in the module's
docstrings, is that the date-based status must be *derived at read
time* from due date + lifecycle state + as-of: an open finding due
2026-06-30 derives `"open"` at as_of 2026-06-30 and `"overdue"` at
as_of 2026-07-01. For the canonical pair the test asserts the real
`derive_finding_status` separates them, that the mutant collapses
both to `"open"`, and — via a literal `assertRaises(AssertionError)`
— that treating the mutant's output as the expected output fails. An
end-to-end arm repeats the separation through the store: a past-due
open finding read with `as_of` carries `derived_status == "overdue"`,
which the mutant's prediction cannot satisfy.

## Mutation verification

VERIFIED by the build worker (2026-10-25). The derivation in
`src/grc/store.py` (`derive_finding_status`) was patched so the
overdue branch never fires — the comparison `if _coerce_as_of(as_of)
> due:` was replaced with `if False:` — the exact live counterpart
of the never-firing mutant in `test_negative_control.py` — and the
full suite was run: **118 tests ran, 8 failed**:

- `test_findings.TestDerivedStatus.test_overdue_after_due_date`
- `test_findings.TestDerivedStatus.test_list_findings_with_as_of_attaches_derivation`
- `test_findings.TestDerivedStatus.test_stored_record_carries_no_derived_status`
- `test_negative_control.TestNegativeControlMutantDerivation.test_real_derivation_separates_the_canonical_pair`
- `test_negative_control.TestNegativeControlMutantDerivation.test_mutant_also_collapses_in_progress`
- `test_negative_control.TestNegativeControlEndToEnd.test_past_due_open_finding_reads_overdue_in_store`
- `test_posture.TestPostureCounts.test_open_and_overdue_counts_use_the_derivation`
- `test_service.TestFullFlow.test_full_flow`

The failures span every surface that depends on the derivation: the
pure function (both negative-control arms and the end-to-end arm),
the store's as-of reads, the posture overdue count, and the HTTP
full flow. `store.py` was then restored from the pre-mutation copy
kept at `tests/store.py.premutation` (SHA-256
e2eac653fb99f97b2a8348f0814eb2b65caa3fc6da0e4103897da67ff3369eeb,
verified identical to the pre-mutation hash) and the suite re-run:
**118 tests, OK**. The suite catches this defect class; the negative
control is not decorative.

**Additions re-run (2026-10-31).** The core is unchanged by the
remainder additions, so the same drill was re-run on the enlarged
tree: the same patch (`if _coerce_as_of(as_of) > due:` →
`if False:` in `derive_finding_status`) and the full suite ran:
**132 tests, 10 failures** — the original 8 above, plus 2 from the
new `test_additions.py` (`test_halo_poam_finding_lifecycle_and_derivation`
and `test_workiva_risk_records_and_counts_only_posture`, both of
which read overdue state derived by the mutated function). Raw
failure list: `../scratch/additions_mutation_failures.txt`.
`store.py` was restored from `tests/store.py.premutation` and
verified SHA-256-identical
(e2eac653fb99f97b2a8348f0814eb2b65caa3fc6da0e4103897da67ff3369eeb);
the suite re-ran: **132 tests, OK**.

## Final GAPS batch module

| File | Covers (Batch) |
|---|---|
| `test_gaps_batch.py` | Final GAPS batch extension surface (`src/grc/extensions.py`, entries idx 353–359; dispositions in `../BATCH.md`) — collection-source / validation-job / validation-report records (report leaves the core evidence record byte-identical), feed definitions + receipts (a receipt creates no core indicator result or finding; non-integer counts rejected), scan jobs / reports / verbatim priority records (a scan report creates no core finding; priority leaves the finding byte-identical), KSI run / report records (a run report creates **no** core indicator result), reported-value records (verbatim labels; the core posture summary is byte-identical before/after), enclave environment / operation records, package records (exact key set — no figures stored) + the package view derived at read (tracks registry state; other systems excluded), the extension summary's counts, RBAC denials for the viewer across the surface, extension writes audited under `ext_` actions, and the no-score recursive scan over every extension record kind and both derived views |

**Batch negative control (fresh, for the new code).**
`TestPackageDerivationNegativeControl` pins the package
manifest's overdue figure: it is *derived at read* through the
single seam `_package_overdue_count` in `extensions.py`, which
applies the core's `derive_finding_status` to each stored
finding. For the canonical fixture (one open finding due
2026-06-30) the real view derives overdue 1 at as_of 2026-07-01
and 0 on the due date; the never-count mutant (an in-suite
subclass returning 0 unconditionally) collapses both to 0, and
treating the mutant's output as the expected output fails via
a literal `assertRaises(AssertionError)`.

**Batch mutation verification.** VERIFIED by the batch build
worker (2026-11-07). The seam's `return count` line in the real
`src/grc/extensions.py` (line 924, inside
`_package_overdue_count`; patched by line number because the
same text occurs once more as a substring of the summary
helper's `return counts` at line 1015) was replaced with
`return 0` and the full suite was run: **161 tests ran,
exactly 4 failed**, all in `test_gaps_batch.py`:

- `test_gaps_batch.TestPackages.test_package_view_derives_from_core_records`
- `test_gaps_batch.TestPackages.test_package_view_tracks_registry_state`
- `test_gaps_batch.TestPackageDerivationNegativeControl.test_real_derivation_separates_the_canonical_pair`
- `test_gaps_batch.TestPackageDerivationNegativeControl.test_mutant_output_as_expectation_fails`

`extensions.py` was then restored from the pre-mutation copy
kept at `../scratch/extensions.py.premutation` (SHA-256
d56ef7b13a65146d995a8bac3abaf62d2ad3c082a4c6e10cbebe1a5a2bec310d,
verified identical to the pre-mutation hash) and the suite
re-run: **161 tests, OK**. Status after the batch:
**161 tests, OK**.

## Final GAPS batch module — remainder-addition unit

| File | Covers (Batch, addition section) |
|---|---|
| `test_gaps_batch_addition.py` | Second batch unit's extension surface (`src/grc/extensions_addition.py`, entries idx 571–577; dispositions in `../BATCH-ADDITION.md`) — policy lifecycle records over evidence/framework subjects (bad subject and unknown subject rejected, no id consumed), the stage-event transition table (illegal transitions rejected whole, rejected → redraft → retire path, retired terminal), the filer-may-not-approve separation (denied approval consumes no event id), agent definitions / runs / reports (a run and its report leave the core posture identical and create no core finding, assessment, or result), generation requests / reports (bad kind and unknown assessment rejected; a report leaves the core assessment byte-identical, creates no core evidence, and rejects an unknown filed-evidence reference), connector definitions / sync receipts (non-integer counts rejected; a receipt reporting 500 records imports no core records), configuration items (duplicate reference rejected, `discovered_here: False`), tickets (stored record carries no status; current status derived at read from the event stream), SLA policies held as data (`evaluated_here: False`), personnel records (exact key set — opaque references only), certification records (currency derived at read: current on the expiry date, expired after it; malformed date rejected), verbatim training / quality-event / corrective-action / maintenance records, connected-report records (data-point values verbatim as labels; the derived view's counts track registry state while the stored record gains no figure), the viewer denied every addition write, addition writes audited under `exta_` actions, and the no-score recursive scan over every addition record kind and view |

**Addition negative control (fresh, for the new code).**
`TestPolicyStageDerivationNegativeControl` pins the policy
lifecycle's current stage: it is *derived at read* from the
stage-event stream by the single seam `_derive_policy_stage`
in `extensions_addition.py` — the stage of the most recent
event. For the canonical stream (drafted → in_review →
approved) the real derivation separates it as `"approved"`;
the first-event mutant (an in-suite function reading
`events[0]`) collapses it to `"drafted"`, and treating the
mutant's output as the expected output fails via a literal
`assertRaises(AssertionError)`.

**Addition mutation verification.** VERIFIED by the addition
batch build worker (2026-11-07). The seam's
`return events[-1]["stage"]` line in the real
`src/grc/extensions_addition.py` (occurrence count asserted 1
before patching) was replaced with
`return events[0]["stage"]` and the full suite was run:
**194 tests ran, exactly 9 errors**, all in
`test_gaps_batch_addition.py` — the mutant freezes the derived
stage at `drafted`, so the `approved` transition is itself
rejected and every flow that drives a lifecycle to approval
errors:

- `test_gaps_batch_addition.TestPolicyLifecycle.test_stage_flow_derives_current_stage_at_read`
- `test_gaps_batch_addition.TestPolicyLifecycle.test_illegal_transition_rejected_and_consumes_no_id`
- `test_gaps_batch_addition.TestPolicyLifecycle.test_approval_separation_of_duties`
- `test_gaps_batch_addition.TestPolicyStageDerivationNegativeControl.test_real_derivation_separates_the_canonical_pair`
- `test_gaps_batch_addition.TestPolicyStageDerivationNegativeControl.test_mutant_collapses_to_the_first_event`
- `test_gaps_batch_addition.TestPolicyStageDerivationNegativeControl.test_mutant_output_as_expectation_fails`
- `test_gaps_batch_addition.TestAdditionInvariants.test_no_score_keys_anywhere_on_the_addition_surface`
- `test_gaps_batch_addition.TestAdditionInvariants.test_addition_writes_audited_under_exta_actions`
- `test_gaps_batch_addition.TestAdditionInvariants.test_addition_summary_counts`

`extensions_addition.py` was then restored from the
pre-mutation copy kept at
`../scratch/extensions_addition.py.premutation` (SHA-256
b5e82fe296446b9c956f42757522abbbca704986db1db2d7c8bcd52425ca192a,
verified identical to the pre-mutation hash) and the suite
re-run: **194 tests, OK**. Status after the addition batch:
**194 tests, OK**.

## Interpretation notes

Where the contract left a shape open, the suite follows the
contract's most literal reading:

- "Open findings" in posture counts the lifecycle states `open`,
  `in_progress`, and `accepted_risk` (a risk-accepted POA&M item is
  still an open item until it is closed or returns to work); the
  derivation's overdue states are exactly `open` / `in_progress`, so
  a risk-accepted finding is never overdue.
- Overdue is strict: an open finding is overdue only when the as-of
  date is *after* the due date; on the due date itself it is still
  current.
- `get_finding` / `list_findings` without `as_of` return exactly the
  stored fields — that is how the suite shows the stored record
  carries no derived status key — and with `as_of` the returned
  copies gain `derived_status`.
- Statuses the contract says are "recorded verbatim" (indicator
  result status, finding severity, assessment result, evidence
  validation status) are asserted verbatim with deliberately
  non-canonical strings (vendor wording, mixed case) so any
  normalization would fail the suite.
- Over HTTP, creation endpoints are asserted as exactly 201, auth
  failures as exactly 401, permission failures as exactly 403, and
  the list endpoints with their wrappers (`{"frameworks": [...]}`,
  `{"controls": [...]}`, `{"systems": [...]}`, `{"indicators":
  [...]}`, `{"results": [...]}`, `{"evidence": [...]}`, `{"findings":
  [...]}`, `{"assessments": [...]}`, `{"authorizations": [...]}`,
  `{"entries": [...]}`); `/posture` is the bare summary dict.
