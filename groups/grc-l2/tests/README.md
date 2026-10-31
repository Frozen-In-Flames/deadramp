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
