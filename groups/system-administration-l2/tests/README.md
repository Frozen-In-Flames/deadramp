# Tests — System Administration L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/system-administration-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 138 tests
```

Status: **138 tests, OK** (71 at singleton delivery; 78 after the
remainder additions — see the additions row and drill re-run
below; 107 after the final GAPS batch addition unit — see the
batch row and the latest-state drill record below; 138 after the
final GAPS batch singleton unit — see the singleton row and the
drill record at the end).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 11 Access control — exact permission matrix, `require()`; audit_read admin-only |
| `test_organizations.py` | 7 | 1 Organizations — pinned record shape (exactly six keys), duplicate refs, membership boundary, member management, read-only viewer |
| `test_systems.py` | 7 | 2 Managed system registry — pinned record shape (exactly nine keys, no live-system identifier field), per-org ref uniqueness, kind validation, retire lifecycle |
| `test_applications.py` | 5 | 3 Application registry — pinned record shape (exactly eight keys), hosting-system linkage, cross-org system rejected, retire lifecycle |
| `test_requests.py` | 9 | 4 Service request records, 5 Derived status — pinned stored shape (exactly ten keys, no derived key stored), due-date validation, lifecycle, cancel restricted to requester or admin, overdue derived at read (before / after / due-today / resolved cases) |
| `test_changes.py` | 8 | 6 Change records — pinned creation shape, AC-5 requester/decider separation, decision fields added at decision, close adds `closed_utc` and modifies no system or application record, cancel restricted to requester or platform admin |
| `test_controls.py` | 5 | 7 Control inheritance records — pinned shape (exactly eight keys), all three sources accepted, duplicate control per system rejected, cross-org system rejected |
| `test_reporting.py` | 4 | 8 Search, 9 Summary — literal substring search over accessible records only, counts-only summary including requests by status and the derived overdue count, controls by source |
| `test_service.py` | 8 | 10 REST API — live HTTP: 401/403/404/400 semantics, the full organization/system/application/request/change/control flow over HTTP (including `?as_of=` derived overdue, and AC-5 enforced over HTTP), denied attempts audited with `:denied`, audit endpoint admin-only |
| `test_audit.py` | 4 | 12 Audit log — mutation recording, entry shape, append-only (no mutation API), JSONL persistence round-trip |
| `test_main_cli.py` | 1 | CLI — `python -m sysadmin serve` subprocess answers `/health` |
| `test_store_validation.py` | 3 | Cross-cutting SI-10 — failed operations consume no id and change nothing; no score/rating/health/posture key on any view (recursive scan) |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_additions.py` | 7 | Remainder additions (unit `addition:system-administration-l2`) — spec integrity: 9 sheets with the shipped sheet first and unchanged (8 claims; group total 9), exact census membership, house schema, taxonomy/verbatim-evidence audit, the exact claim map (1 claim over 1 fork, 7 zero-claim forks); the virtualization Extended honesty pin (no engine entry point on the store) and the claimant's records-substrate case (pinned nine-key system shape) |
| `test_gaps_batch_addition.py` | 29 | Final GAPS batch addition unit (Remainder Addition section, idx 552–560) — per-entry record shapes and honesty labels for the delivery platform, observability stub, ITSM/ITAM, discovery/CMDB, PPM, DEX, GIS, backup/DR stub, and security-operations surfaces; derived-never-stored current states; recursive no-score key scan; access discipline (denied writes audited `:denied`, non-members reach nothing, failed writes consume no id); the fresh latest-state negative control (below) |
| `test_gaps_batch_singleton.py` | 31 | Final GAPS batch singleton unit (Singleton 54 section, idx 515–520) — per-entry record shapes and honesty labels for the administration-operation, virtualization, and HA surfaces; the stub labels on the provisioning, hosting-runtime, and CSP-platform reference implementations; derived-never-stored current states; recursive no-score key scan; access discipline (denied writes audited `:denied`, non-members reach nothing, failed writes consume no id); the fresh latest-state negative control (below) |
| `sysadmin_helpers.py` | — | Canonical fixture: organization `AGENCY-1` by bob, erin added as staff member (the canonical decider), system `SYS-OS-1` (operating_system, platform `PLAT-A`), application `APP-PORTAL`, service request due 2026-06-10 so `as_of` 2026-06-05 → not overdue and 2026-06-15 → overdue; outsider dave in no organization |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is **derived request overdue status**: a service request is
overdue when it is still open or in progress and its due date is
before the read date (resolved and cancelled requests are never
overdue), derived at read and never stored. The mutant is a
`SysadminStore` subclass (`MutantSysadminStore`) whose
`_is_overdue` always returns `False`. The tests assert the
canonical expectations (not overdue at the 2026-06-05 read clock,
overdue at 2026-06-15), that the implementation matches them in
both the request view and the organization summary, and — via a
literal `assertRaises(AssertionError)` — that the canonical
expectation rejects the mutant's outcome (the mutant reports not
overdue at the after-due read clock).

## Mutation verification

VERIFIED for this group: `_is_overdue` in the real
`src/sysadmin/store.py` was patched to return `False`
unconditionally and the suite was run against the patched
implementation.

- Patched run: **71 ran, exactly 6 failed**:
  - `test_negative_control.TestNegativeControlDerivedOverdue.test_canonical_expectation`
  - `test_negative_control.TestNegativeControlDerivedOverdue.test_implementation_matches_canonical_in_summary`
  - `test_reporting.TestSummary.test_summary_counts`
  - `test_requests.TestRequests.test_creation_shape_pinned_and_view_adds_overdue_only`
  - `test_requests.TestRequests.test_overdue_derived_at_read`
  - `test_service.TestService.test_full_flow_over_http`
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`46c4f2dc…`, recorded in
  `scratch/store.py.sha256`); the suite is green again (71/71).
  Raw drill output is in `scratch/mutation-run.txt`.

The failing set is exactly the derivation-dependent set: every
failure needs a True overdue derivation (at a pinned `as_of`, in
the summary's count at the real read clock, in the creation view
at the real read clock, or over HTTP), the not-overdue and
resolved cases still pass under the mutant (the mutant agrees
with the correct answer there, by construction), the
stored-record key pins are untouched by this mutation, and the
mutant's own subclass test passes by construction, as expected.

**Additions re-run (2026-10-31).** The remainder additions
changed no core code, so the drill was re-run in this tree
against the enlarged suite: `_is_overdue` patched to `return
False` in the real `src/sysadmin/store.py` → **78 ran, exactly
6 failed**, the identical failure set to the shipped drill above
(the 7 additions tests do not depend on the derivation and pass
under the mutant, as constructed). `store.py` was restored from
`scratch/store.py.premutation.additions` and verified
SHA-256-identical to the shipped hash (`46c4f2dc…`); the suite
is green again (78/78). Raw drill output is in
`scratch/additions_mutation_run.txt`.

## Interpretation notes

- Derived overdue is pinned twice over: once through the public
  request views and the summary, and once by asserting the raw
  stored request record (`store._requests`) carries exactly its
  ten stored keys and no `overdue` key at all.
- Lifecycle statuses (`open` / `in_progress` / `resolved` /
  `cancelled` for requests; `registered` / `retired` for systems
  and applications; the change lifecycle) are event-driven, not
  date-driven, so they *are* stored — the distinction from
  derived overdue is deliberate and stated in the store's module
  docstring.
- A request due *today* is not overdue: the derivation is
  `due_date < read date`, pinned by
  `test_due_today_is_not_overdue`.
- Closing a change is pinned as a records-only event:
  `test_close_approved_change_modifies_no_system_or_application`
  compares the raw stored system and application records before
  and after the close and requires them identical. The work that
  would carry a change out is Extended.
- Control records carry dispositions verbatim and nothing else:
  the recursive no-score scan in `test_store_validation.py`
  covers the control view and the summary's `controls_by_source`
  counts, so no posture value can appear anywhere.
- An empty search query returns no records in any category: the
  search is a literal substring search and the empty-needle case
  is defined as no search (the contract names the searched
  fields, not an empty-query behavior; this is the adjudicated
  reading, recorded here).
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.
- Two test expectations were corrected during the build (test
  bugs, not implementation bugs): the creation view of the
  canonical request derives overdue against the *real* read
  clock, under which the June 2026 fixture due date is already
  past, so the view correctly reads `overdue == True` at
  creation; the pinned before/after cases run through explicit
  `as_of` values. Both corrected tests carry comments saying so.

## Final GAPS batch addition — fresh negative control

**`test_gaps_batch_addition.py`** adds the batch unit's own
negative control for its new code (the core is unchanged, so the
signature drill above stands as-is). The addition module's
signature derivation is **latest recorded state label wins**:
tickets, assets, projects, and security cases carry append-only
reported state labels, and the current state derives at read as
the *last* label recorded (`SysadminAddition._latest_state_label`).
The in-suite control (`TestLatestStateNegativeControl`) asserts
the canonical expectation (a ticket labelled `reported_open`
then `reported_resolved` reads `reported_resolved`), that the
implementation matches it in both the ticket view and the ITSM
summary's counts, and — via a literal `assertRaises(AssertionError)`
— that an earliest-label mutant subclass violates the canonical
expectation.

**Mutation verification (2026-11-07).** `_latest_state_label` in
the real `src/sysadmin/addition.py` was patched to return
`state_records[0]["state_label"]` (earliest instead of latest)
and the suite was run against the patched implementation.

- Patched run: **107 ran, exactly 6 failed**, all in
  `test_gaps_batch_addition.py`:
  - `test_gaps_batch_addition.TestLatestStateNegativeControl.test_canonical_expectation`
  - `test_gaps_batch_addition.TestLatestStateNegativeControl.test_implementation_matches_canonical`
  - `test_gaps_batch_addition.TestItsmItam.test_current_state_derives_latest_label`
  - `test_gaps_batch_addition.TestItsmItam.test_asset_state_derives_and_summary_counts`
  - `test_gaps_batch_addition.TestPortfolioManagement.test_portfolio_view_counts_by_derived_state`
  - `test_gaps_batch_addition.TestSecurityOperations.test_case_state_derives_and_finding_is_verbatim`
- `addition.py` was then restored from
  `scratch/addition.py.premutation` and verified
  **SHA-256-identical** (`scratch/addition.py.sha256`); the suite
  is green again (107/107). Raw failing set in
  `scratch/addition_mutation_run.txt`.

The failing set is exactly the latest-state-derivation-dependent
set: every failure needs a second recorded label to supersede a
first. Single-label and no-label cases still pass under the
mutant (it agrees with the correct answer there, by
construction), the record-shape and honesty-label pins are
untouched by this mutation, and the mutant subclass's own test
passes under it by construction, as expected.

## Final GAPS batch singleton — fresh negative control

**`test_gaps_batch_singleton.py`** adds the singleton unit's own
negative control for its new code (the core and the addition
module are unchanged, so both drills above stand as-is). The
singleton module's signature derivation is **latest recorded
state label wins**: virtual instances and HA configurations
carry append-only reported labels, and the current state derives
at read as the *last* label recorded
(`SysadminSingletonExtensions._latest_state_label`). The
in-suite control (`TestSingletonLatestStateNegativeControl`)
asserts the canonical expectation (an HA configuration labelled
`reported_healthy` then `reported_failover` reads
`reported_failover`; an instance's summary counts it under its
latest label), and — via a literal
`assertRaises(AssertionError)` — that an earliest-label mutant
subclass violates the canonical expectation.

**Mutation verification (2026-11-07).** `_latest_state_label`
in the real `src/sysadmin/singleton_extensions.py` was patched
to return `state_records[0]["state_label"]` (earliest instead of
latest) and the suite was run against the patched
implementation.

- Patched run: **138 ran, exactly 5 failed**, all in
  `test_gaps_batch_singleton.py`:
  - `test_gaps_batch_singleton.TestSingletonLatestStateNegativeControl.test_canonical_expectation`
  - `test_gaps_batch_singleton.TestSingletonLatestStateNegativeControl.test_implementation_matches_canonical_in_summary`
  - `test_gaps_batch_singleton.TestHighAvailability.test_current_state_derives_latest_event`
  - `test_gaps_batch_singleton.TestHighAvailability.test_summary_counts`
  - `test_gaps_batch_singleton.TestVirtualization.test_current_state_derives_latest_label`
- `singleton_extensions.py` was then restored from
  `scratch/singleton_extensions.py.premutation` and verified
  **SHA-256-identical** (`scratch/singleton_extensions.py.sha256`);
  the suite is green again (138/138). Raw drill output is in
  `scratch/singleton_mutation_run.txt`.

The failing set is exactly this unit's
latest-state-derivation-dependent set, on both derivation
surfaces (HA configurations and virtual instances). No core or
addition-unit test failed: the seam is new code, and every
failure needs a second recorded label to supersede a first.
