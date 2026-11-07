# Tests — GRC L1 singleton build (Group 43)

Stdlib `unittest` only. Every test docstring names the core function /
spec claim / control family it traces to.

This suite is the shipped Group 33 (GRC L2) suite, reused (see
`../scratch/reuse-note.md`): 13 of 14 files byte-identical, one
docstring line changed in `grc_helpers.py`, zero test-logic changes.
The mutation drill below was performed **fresh in this tree**.

## Run

```bash
cd groups/grc-l1
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **118 tests, OK** against the implementation in
`../src/`, verified by the build coordinator's own run (2026-10-31).
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
| `test_negative_control.py` | Negative control (below) |
| `test_audit.py` | 10 Audit log — entry keys (AU-3 content, stated at this tier as an implementation property traced to AU-2/AU-3 on the FedRAMP Low side only), actor normalization, append-only surface (no update/delete API, `entries()` returns copies), JSONL persistence + reload, the store recording each mutation action (`framework_create`, `control_create`, `system_create`, `indicator_create`, `indicator_result_record`, `evidence_create`, `evidence_review`, `finding_create`, `finding_transition`, `assessment_create`, `authorization_create`, `authorization_transition`) incl. the transition `details` payload, reads and failed ops writing nothing |
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

VERIFIED fresh in this tree by the build coordinator (2026-10-31).
The derivation in `src/grc/store.py` (`derive_finding_status`) was
patched so the overdue branch never fires — the comparison
`if _coerce_as_of(as_of) > due:` was replaced with `if False:` — the
exact live counterpart of the never-firing mutant in
`test_negative_control.py` — and the full suite was run: **118 tests
ran, 8 failed** (raw output in `../scratch/mutation-run.txt`):

- `test_findings.TestDerivedStatus.test_overdue_after_due_date`
- `test_findings.TestDerivedStatus.test_list_findings_with_as_of_attaches_derivation`
- `test_findings.TestDerivedStatus.test_stored_record_carries_no_derived_status`
- `test_negative_control.TestNegativeControlMutantDerivation.test_real_derivation_separates_the_canonical_pair`
- `test_negative_control.TestNegativeControlMutantDerivation.test_mutant_also_collapses_in_progress`
- `test_negative_control.TestNegativeControlEndToEnd.test_past_due_open_finding_reads_overdue_in_store`
- `test_posture.TestPostureCounts.test_open_and_overdue_counts_use_the_derivation`
- `test_service.TestFullFlow.test_full_flow`

The failing set is identical to Group 33's drill at L2 — the same
eight surfaces that depend on the derivation: the pure function
(both negative-control arms and the end-to-end arm), the store's
as-of reads, the posture overdue count, and the HTTP full flow.
`store.py` was then restored from the pre-mutation copy kept at
`tests/store.py.premutation` (SHA-256
e2eac653fb99f97b2a8348f0814eb2b65caa3fc6da0e4103897da67ff3369eeb,
verified identical to the pre-mutation hash) and the suite re-run:
**118 tests, OK**. The suite catches this defect class; the negative
control is not decorative.

## Interpretation notes

Where the contract left a shape open, the suite follows the
contract's most literal reading (inherited from Group 33, unchanged):

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

## Final GAPS batch coverage (Singleton 43 section, idx 415–418)

`test_gaps_batch.py` (24 tests) pins the batch extension surface
in `../src/grc/extensions.py` (`GrcExtensions`); see `../BATCH.md`
for the per-entry dispositions. All pre-existing modules are
byte-identical to their pre-batch state (SHA-256 verified against
`../scratch/prebuild-src.sha256`).

| File | Covers (batch) |
|---|---|
| `test_gaps_batch.py` | idx 415 questionnaire automation (reference) — definition shape + stub labels (`reference_stub`, `administered_here` / `reuse_applied_here: False`), questions held as data verbatim, unknown system rejected with no id consumed, response answers verbatim (non-string answer / non-mapping rejected), unknown questionnaire consumes no response id, view derives response counts + latest reported status while the stored definition carries no derived key; idx 416 Trust Center publication (built) — stored record's exact 8-key set with no figures, view derives the core posture counts and tracks registry state (a finding added after registration appears, overdue via the core derivation) while the stored record never gains a figure, releases verbatim with derived count + latest label; idx 417 vendor risk assessment (reference) — rule shape (`recorded_rules_only`, `applied_here: False`) and the rule record byte-identical after an assessment is recorded against it, assessment outcome + reported label verbatim with `evaluated_here` / `computed_here: False`, **no core finding created** and core posture unchanged, summary counts verbatim labels only, unknown system/rule rejected with no id consumed; idx 418 monitoring & collection (reference) — source shape + stub/transport labels, bad kind rejected, observation intake verbatim (optional control validated against the catalog; unknown control rejects with no id consumed) creating **no core indicator result**, collection runs with reported artifact counts (bool/float/negative rejected) creating **no core evidence**, source view deriving counts + latest status + the summed *reported* artifact total; cross-cutting invariants — the founding no-score recursive key scan over every record kind, every view, both summaries, and the embedded core posture; extension writes audited under `ext_` actions; viewer writes denied with no forged audit entries; extension summary counts; and the fresh negative control below |

### Batch negative control — the latest-label seam

`TestLatestLabelNegativeControl` implements the batch unit's
fresh mutant for the extension's derivation seam
`GrcExtensions._latest_label`: views derive their "latest" label
(the latest response status, the latest release label, the
latest observation status) from the recorded stream at read, and
the value is never stored. The canonical expectation is that the
latest label is the **most recently recorded** one; a mutant
seam that reads the **earliest** record must misstate it. The
test states the expectation, asserts the real implementation
meets it across two families' views, asserts the
earliest-reading subclass mutant misstates both, and — via a
literal `assertRaises(AssertionError)` — that treating the
mutant's output as the expected output fails.

### Batch mutation verification

VERIFIED by the batch coordinator (2026-11-07). The seam in
`src/grc/extensions.py` was patched so it reads the earliest
record — `return records[-1][key] if records else None` replaced
with `return records[0][key] if records else None` (the target
text asserted to occur exactly once before patching) — and the
full suite was run: **142 tests ran, exactly 4 failed** (raw
output in `../scratch/gaps_mutation_run.txt`), all in
`test_gaps_batch.py`:

- `TestQuestionnairesReference.test_response_verbatim_and_view_derives`
- `TestPublicationsBuilt.test_releases_verbatim_and_view_derives_latest`
- `TestMonitoringReference.test_source_view_derives_counts_and_latest`
- `TestLatestLabelNegativeControl.test_canonical_latest_is_most_recent`

The failing set is exactly the surfaces that depend on the
latest-label derivation: one canonical derivation test per
family that derives a latest label (questionnaire view,
publication view, source view) plus the negative control's
canonical arm. (The in-suite mutant subclass overrides the seam
itself, so its legs are unaffected by the file patch — the same
shape as the sibling units' drills.) `extensions.py` was then
restored from the pre-mutation copy kept at
`../scratch/extensions.py.premutation` (SHA-256
99838d1be2ad52c2d63b57cebab94ca308486410ed178a74b1920e168999a874,
verified identical to the pre-mutation hash) and the suite
re-run: **142 tests, OK**. The suite catches this defect class;
the negative control is not decorative.
