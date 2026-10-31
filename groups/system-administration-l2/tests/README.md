# Tests — System Administration L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/system-administration-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 71 tests
```

Status at delivery: **71 tests, OK**.

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
