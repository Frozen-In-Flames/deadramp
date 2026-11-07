# Tests — Contact Center L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/contact-center-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 155 tests
```

Status at delivery: **107 tests, OK** against the implementation in
`../src/`; the final GAPS batch unit (below) brought the suite to
**155 tests, OK**. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py` is
empty by design, so package-mode discovery with `-t .` is not the
supported entry point for this group.)

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
| `test_gaps_batch.py` | Final GAPS batch unit — the extension surface (`contact.extensions`), per-entry shapes/labels/derivations, privacy scan, and the batch's fresh SLA negative control (see the batch section below) |
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

## Final GAPS batch unit (2026-11-07)

`test_gaps_batch.py` (48 tests) pins the batch extension surface in
`src/contact/extensions.py` (`ContactExtensions`, wrapping the core
store; all pre-existing core modules byte-identical — `store.py`
still `12709f80…`). Per class:

| Class | Covers |
|---|---|
| `TestPam` | PAM & Zero Trust (idx 152, built) — request shape (exact key set, stored record carries no `current_state`), JIT window validation, outcomes deriving current state at read, session records (`content_held_here` / `monitored_here` False), unknown-agent refusal consuming no id, viewer write denied |
| `TestIdentityRisk` | Identity risk analytics (idx 153, built) — signal shape with no score-shaped key anywhere, `computed_here` False, recommendation↔signal agent binding, counts-only summary |
| `TestClearance` | Personnel-security depth (idx 157, built) — case shape (exact key set), subject must be a core directory agent/contact, outcomes deriving latest state at read, `adjudicated_here` False |
| `TestKnowledgeBase` | KB articles (idx 160, built) — stored article record holds no text (exact key set), revisions append-only with carry-forward, search over current text, no-id-on-failure |
| `TestCsat` | CSAT surveys (idx 161, built) — instrument shape with no score/tally key, scale + rating validation (bool/float/out-of-scale refused), tally derived at read with the mean as an exact rational (13/3), empty-survey tally |
| `TestSlaPolicy` | SLA policy engine (idx 162, built) — policy shape (exact key set), target validation (unknown priority / zero / float / bool / empty refused, no id consumed), policy write admin-only, breach derivation at the seam, uncovered priority never breached, terminal case never breached, breach report counts, policy views leaving the core case record byte-identical |
| `TestSlaPolicyNegativeControl` | Fresh negative control (below) |
| `TestObservabilityStub` | Observability (idx 154, reference) — `reference_stub` True, `collected_here` / `forecast_computed_here` False, reported counts stored verbatim, count validation |
| `TestTelephonyStub` | Voice/telephony (idx 155, reference) — `connected_here` / `media_here` / `routed_here` False, link existence, routing record leaving queue membership untouched, no phone-shaped key |
| `TestFraudStub` | Claims/fraud (idx 156, reference) — rule definitions as data (`executed_here` False, admin-only), findings verbatim with `detected_here` / `adjudicated_here` False, finding leaving the core case byte-identical |
| `TestConnectorStub` | Connectors (idx 158, reference) — `reference_stub` + `reference_transport` True, `connected_here` / `synced_here` False |
| `TestMlStub` | AI/ML (idx 159, reference) — `inference_here` / `trained_here` False; a reported output creates no alert |
| `TestCrossCutting` | Privacy + integrity — recursive forbidden-key scan (no phone/email/ssn-shaped key) over all 22 extension record types built in one store plus a no-score scan over risk/survey/policy records; stub creations changing no core record counts; denied attempt audited as `ext_case_write:denied`; successful mutation audited as `ext_*`; audit failure rolling back the record and its id |

### Batch negative control (fresh, mutation-verified)

`TestSlaPolicyNegativeControl` implements the batch's mutant: a
`ContactExtensions` subclass (`MutantSlaExtensions`) overriding the
single SLA derivation seam `_is_breached_under_policy` to always
return `False`. The traced claim: a covered, open case past its
recorded target must read `breached_under_policy=True` in
`sla_case_view` and count as breached in `sla_breach_report`. The
test asserts the canonical expectation on the real implementation,
that the mutant does NOT produce it, and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails.

VERIFIED by the builder (2026-11-07) with a live drill on the real
implementation: the seam's return line in
`src/contact/extensions.py` (`return now_dt > created_dt +
timedelta(minutes=target)`) was patched to `return False` and the
full suite run: **155 tests ran, exactly 3 failed** —

- `test_gaps_batch.TestSlaPolicy.test_breach_derivation`
- `test_gaps_batch.TestSlaPolicy.test_breach_report_counts`
- `test_gaps_batch.TestSlaPolicyNegativeControl.test_canonical_breaches_and_mutant_does_not`

`extensions.py` was then restored from the pre-mutation copy
(`scratch/extensions.py.premutation`; SHA-256
`b334e9989cf979a16ca3f3346fcb2b70a640e26b23c2b4c8d68a3a796eb90b9e`,
recorded in `scratch/extensions.py.sha256` and verified identical
after restore) and the suite re-run: **155 tests, OK**.
