# Tests — Contact Center L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/contact-center-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 107 tests
```

Status at delivery: **107 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/operator/viewer (16 actions), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording every contract mutation action name, failed ops record nothing |
| `test_directory.py` | Directory — agent (`agt-`) and contact (`ct-`) creation shape/provenance/defaults, get/list, copies-are-copies, validation (empty name, bad skills/attributes/reference), viewer write denied, failed ops consume no ids |
| `test_queues.py` | Queues — `que-` creation, add agent, duplicate membership → `ValidationError`, unknown ids → `NotFoundError`, `list_queue_members` returns agent dicts |
| `test_cases.py` | Cases — creation/validation (types, priorities, due_at parsing, referenced ids), assignment, full lifecycle + reopen + cancel paths, invalid transitions, breach derivation (overdue open/in_progress breached; future/no/exact due not breached; terminal statuses never breached; `now` as string/datetime/None; derived-not-stored), list filters, no-id-on-failure |
| `test_callbacks.py` | Callbacks — `cb-` scheduling/validation, derived states scheduled/overdue/completed/cancelled (stored `status` kept, `state` derived, never stored), terminal-transition guards (complete/cancel only from scheduled) |
| `test_interactions.py` | Interactions — `int-` recording, all channels/directions, validation + linked-id checks, immutability (no update/delete API on the store; returned records are copies), case filter |
| `test_alerts.py` | Alerts — `alr-` raising, all severities, lifecycle raised→acknowledged→resolved (+ direct resolve), lifecycle guards, unknown ids |
| `test_rules.py` | Rules registry — `rule-` creation at version 1 with versions list, `case_type` = known type or `all`, versioned updates carrying unchanged fields forward, **admin-only write (operator denied)**, copies-are-copies |
| `test_reports_search.py` | Reports + search — report shape/counts (cases by status/type/queue incl. `unassigned`, breached at `now`; interactions by channel/outcome incl. `none`; alerts by severity/status; callbacks by derived state), now-dependence of breach counts, empty store; search shape `{people, cases, interactions, alerts}`, name+reference / subject / summary+external_ref / message matching, literal-not-regex, empty query → `ValidationError` |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer write + rule_write for operator (denied attempts audited with `:denied`), full flow (agent → contact → queue+member → case → assign/transition → callback → interaction → alert → rule create/PATCH → report/search → audit), `audit_read` admin-only, 400/404 envelopes, `?now=` derivation on case/callback/report endpoints |
| `test_main_cli.py` | `python -m contact serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `contact_helpers.py` | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a ContactStore + AuditLog + an agent + a contact + a queue with the agent in it (created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `ContactStore` subclass (`MutantContactStore`) overriding the two
derivation points — `_is_breached` always returns `False` and
`_callback_state` never returns `overdue`. The traced claim, named in
the module's docstrings, is that **breach/state derivation happens at
read time**: an overdue open case must read `breached=True` (and a
report at that `now` must count it breached), and an overdue scheduled
callback must read `state='overdue'` while its stored `status` stays
`scheduled`. For each canonical case (overdue case, overdue callback)
the test asserts three things: the canonical expectation (derived
value from the real implementation, including the report counts),
that the mutant would NOT produce that expectation (it reads
not-breached / scheduled, and its report counts zero breached), and —
via a literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails.

## Mutation verification

VERIFIED by the builder (2026-10-25), live drill performed on the
real implementation (not just the subclass mutant). The body of
`ContactStore._is_breached` (`src/contact/store.py`) — the single
derivation point for case SLA breach — was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`, so an overdue open case never read
breached. The full suite was run: **107 tests ran, 8 failed** —

- `test_cases.TestBreachDerivation.test_breach_is_derived_not_stored`
- `test_cases.TestBreachDerivation.test_in_progress_past_due_breached`
- `test_cases.TestBreachDerivation.test_now_forms`
- `test_cases.TestBreachDerivation.test_overdue_open_case_breached`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_case_breached_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_breach_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`12709f808e05a7bcfb7bb6f4b116ace15ede3e553f6d539e561bf50ee9054138`,
recorded in `scratch/store.py.sha256` and verified identical after
restore) and the suite re-run: **107 tests, OK**. The suite catches
this defect class; the negative control is not decorative.
