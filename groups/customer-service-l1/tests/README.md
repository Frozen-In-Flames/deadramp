# Tests — custsvc (Group 26: Customer Service, L1)

Run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**80 tests, all passing** (Python stdlib `unittest` only, zero
third-party dependencies). Originally 69; the remainder addition
below added 11 (`test_additions.py`).

## Coverage map

| File | Covers |
|---|---|
| `test_access.py` | Core 10 — RBAC matrix: admin ⊇ all; agent writes cases/requesters/responders/alerts/schedules but NOT rules or audit; viewer read-only, no audit. Unknown roles denied. |
| `test_audit.py` | Core 10 — append-only audit: entry shape/order, no update/delete API exists, store mutations recorded with actor names. |
| `test_requesters.py` | Core 2 — requester privacy is structural: exact record key set pinned, no contact fields exist, duplicate refs rejected. |
| `test_cases.py` | Core 1 + 3 — case lifecycle (incl. invalid moves rejected, reopen from resolved/closed), assignment/reassignment, list filters. |
| `test_breach.py` | Core 4 — breach derived at read: past-due open = breached; future/no due = not; terminal status = never; same record reads differently at different `now` (derived, not stored). |
| `test_alerts.py` | Core 5 — alert ingest shape, opaque source refs, ack/resolve, link to case, bulk ingest atomicity (bad batch records nothing). |
| `test_schedules.py` | Core 6 — on-call derivation: anchor week, period rollover, rotation wrap, before-anchor backwards wrap, daily rotations; validation. |
| `test_rules.py` | Core 8 — rule registry records only: agent cannot write rules; a matching rule changes NO state (execution is Extended, pinned by test). |
| `test_status_reports.py` | Core 7 + 9 — status derivation (operational/degraded/outage), internal updates never leak into the public view, report counts, registry search. |
| `test_service.py` | HTTP layer — health, 401 + denied-audit, role mismatch 401, viewer 403 + denied-audit, full flow incl. breach over HTTP, audit admin-only, rule write admin-only. |
| `test_main_cli.py` | CLI — no command exits 2, TLS cert/key pairing enforced, parser defaults. |
| `test_negative_control.py` | The load-bearing assertions for the mutation drill below. |
| `test_additions.py` | Remainder addition (Zendesk, FR1821856903) — spec integrity for a ZERO-CLAIM fork: sheet order/membership, the literal empty claim table, the originals' claim tables pinned as shipped, all-16 zero-claim set, census citations verified tagging nothing, near-miss pins, group totals (3 forks / 8 claims); plus 2 carried-substrate cases (help-desk flow with public status; breach derivation — trips under the drill). |

## Negative control — mutation record

**Drill performed** (Oct 25, 2026): `CustsvcStore._is_breached` in
`src/custsvc/store.py` was patched to `return False` unconditionally
(breach never derived). Result: **7 failures** across 4 files —

- `test_negative_control.py`: both tests (overdue case reads breached;
  breach counted in report and status view)
- `test_breach.py`: `test_past_due_open_case_is_breached`,
  `test_breach_is_derived_not_stored`
- `test_status_reports.py`: `test_breached_normal_case_is_degraded`,
  `test_report_counts`
- `test_service.py`: `test_full_flow` (breach asserted over HTTP)

The file was then restored from `scratch/store.py.premutation` and
verified byte-identical (SHA-256 `05c749f3…`, recorded in
`scratch/store.py.sha256`); the suite returned to **69/69 green**.
An oracle that passes with breach derivation removed would be testing
that code ran, not that breach state is derived — this control is the
filter against that.

**Drill re-run (remainder addition, Oct 31, 2026):** the core is
unchanged by the Zendesk addition, so the same drill was re-run in
this tree: `_is_breached` patched to `return False` unconditionally
(scoped replacement of the function body in `src/custsvc/store.py`,
pattern asserted to occur exactly once). Result: **80 tests ran,
exactly 8 failures** — the shipped drill's 7 (both
`test_negative_control.py` tests; `test_breach.py`:
`test_past_due_open_case_is_breached`,
`test_breach_is_derived_not_stored`; `test_status_reports.py`:
`test_breached_normal_case_is_degraded`, `test_report_counts`;
`test_service.py`: `test_full_flow`) plus 1 from the additions
module — `test_additions.py`:
`TestZendeskSubstrate.test_due_case_breach_derivation` — tripping
exactly as designed. Raw list in `scratch/additions_mutation_run.txt`.
The file was restored from `scratch/store.py.premutation-additions`
and verified byte-identical (SHA-256 `05c749f3…`); the suite returned
to **80/80 green**.


## Final GAPS batch (test_gaps_batch.py — 46 tests)

The batch adds `test_gaps_batch.py`, one section per GAPS entry
closed by the batch unit (see `BATCH.md` in the group directory):
automation execution requests and verbatim reports (the registry
still never executes), GRC framework/control/mapping records with
counts-only posture derived at read, knowledge-base articles whose
stored record holds tags/provenance only (text lives in append-only
revisions), CSAT surveys with verbatim responses and an exact-
rational (13/3) derived mean, SLA policy records with breach
derived at read (policy views leave the core case byte-identical),
notification records carrying `reference_transport: true` /
`delivered_here: false`, status-page records over the core's
derived public view (`hosted_here: false`), deterministic
count-only analytics, and the three labeled reference families
(detection/orchestration — a run provably creates no alert;
channels — `media_here: false`; AI assistance — the reported case
provably untouched). Cross-cutting tests pin the `ext_*` /
`ext_*:denied` audit actions, audit-failure rollback of record and
id, requester-ref discipline, and stub/core isolation (creating
every stub-family record changes no core record).

Suite total with the batch: **126 tests, all passing** (80 before).

### Fresh negative control: the SLA policy-breach derivation

Breach state under a recorded SLA policy is **derived at read**
from the core case record against the policy's recorded terms at
the seam `CustsvcExtensions._is_breached_under_policy` (in
`src/custsvc/extensions.py`) — the batch's fresh negative control,
in two layers.

In-suite (`TestSlaNegativeControl.test_policy_breach_is_derived`):
the canonical seam derives breach once the recorded target has
passed (a high-priority case viewed 61 minutes after creation
under a 60-minute target is breached); a
`MutantCustsvcExtensions` overriding the seam with a no-op
(`return False`) does not produce that outcome on identical
fixtures; treating the mutant's outcome as the canonical
expectation fails.

External drill (same discipline as the founding drills above):
the real seam's final return
(`return now_dt > created + timedelta(minutes=target)`) was
replaced with `return False` in `src/custsvc/extensions.py` (the
pre-mutation file copied to `scratch/extensions.py.premutation`,
its SHA-256 recorded at `scratch/extensions.py.sha256`, and the
run's failure list logged to `scratch/gaps_mutation_run.txt`).
The full suite then reported:

```text
FAIL: test_policy_breach_is_derived (test_gaps_batch.TestSlaNegativeControl)
FAIL: test_breach_derived_from_recorded_terms (test_gaps_batch.TestSlaPolicies)
FAIL: test_breach_report_counts (test_gaps_batch.TestSlaPolicies)
Ran 126 tests
FAILED (failures=3)
```

Exactly the three tests that depend on policy breach being
derived failed; every other test — founding, addition, and the
rest of the batch — stayed green, so the failures are exactly the
guarantee the derivation tests exist to protect. The file was
restored from the pre-mutation copy (hash verified against the
recorded SHA-256) and the suite returned to **126 tests, OK**.


## Final GAPS batch — second unit (test_gaps_batch_addition.py — 28 tests)

The second batch unit adds `test_gaps_batch_addition.py`, covering
the one OPEN entry of the GAPS.md section "Remainder Addition —
Customer Service L1 (+1 fork)" (see `BATCH-ADDITION.md` in the
group directory): proactive engagement & outreach, built in the
records form the first unit adjudicated for notification
delivery — campaign definitions whose trigger/audience terms are
held as data and provably never evaluated (a matching trigger
creates no attempt and touches no case), suppression records with
a guard seam, outreach attempt records carrying
`reference_transport: true` / `sent_here: false`, and outcome
reports stored verbatim (a full flow leaves the bound core case
byte-identical). Cross-cutting tests pin the stored campaign
record's exact key set, the no-content discipline (content-shaped
kwargs raise `TypeError`; a recursive scan finds no content or
tally key and no float value on any record, view, or summary),
requester-ref discipline (unregistered refs refused everywhere),
the `exta_*` / `exta_*:denied` audit actions on this tier's plain
append-only log, and audit-failure rollback of record and id.

Suite total with the second unit: **154 tests, all passing**
(126 before).

### Fresh negative control: the suppression guard

An outreach attempt to a suppressed requester is **refused
whole** — no record, no id consumed — at the seam
`CustsvcExtensionsAddition._is_suppressed` (in
`src/custsvc/extensions_addition.py`): a requester is suppressed
for a campaign when a suppression record names them with that
campaign's scope or with the global scope. This is the second
unit's fresh negative control, in two layers.

In-suite (`TestSuppressionNegativeControl.
test_suppression_guard_is_load_bearing`): the canonical surface
refuses the attempt; a `MutantCustsvcExtensionsAddition`
overriding the seam with a no-op (`return False`) records the
attempt on identical fixtures; treating the mutant's outcome as
the canonical expectation fails.

External drill (same discipline as the drills above): the seam's
scoped match block (the `campaign_id` scope condition and its
`return True`, asserted to occur exactly once) was patched to
`return False` in `src/custsvc/extensions_addition.py` (the
pre-mutation file copied to
`scratch/extensions_addition.py.premutation`, its SHA-256
recorded at `scratch/extensions_addition.py.sha256`, and the
run's failure list logged to
`scratch/gaps_batch_addition_mutation_run.txt`). The full suite
then reported:

```text
FAIL: test_suppressed_requester_refused_whole (test_gaps_batch_addition.TestOutreachAttempts)
FAIL: test_globally_suppressed_refused_for_any_campaign (test_gaps_batch_addition.TestOutreachAttempts)
FAIL: test_suppression_guard_is_load_bearing (test_gaps_batch_addition.TestSuppressionNegativeControl)
Ran 154 tests
FAILED (failures=3)
```

Exactly the three tests that depend on the suppression guard
failed; every other test — founding, addition, first batch unit,
and the rest of this unit — stayed green, so the failures are
exactly the guarantee the guard tests exist to protect. The file
was restored from the pre-mutation copy (hash verified against
the recorded SHA-256) and the suite returned to **154 tests,
OK**.
