# Tests — Artificial Intelligence (AI) L3-adjacent merged build (FedRAMP High)

Stdlib `unittest` only. Zero third-party imports in `tests/` or
`../src/`. Every test docstring names the UNION-SPEC core function /
spec claim / control family it traces to.

This suite **extends the shipped Group 9 (AI L2) suite**: the L2 tests
were copied whole and pass except for the minimal adaptations listed
below, and new files cover the High-baseline uplifts. Per the Merge
Rule, the merged build inherits the higher tier (High) in full while
reusing the Group 9 code (Apache-2.0, ours) wherever functions
overlap.

## Run

```bash
cd groups/ai-l3
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **193 tests, OK** against the implementation in
`../src/` (153 inherited from Group 9 — 146 carried up unchanged in
count plus 7 added inside adapted files — and 40 new uplift tests).
(Run exactly as above: helpers are imported as a top-level module
from the tests directory and `tests/__init__.py` is empty by design,
so package-mode discovery with `-t .` is not the supported entry
point for this group.) Test scratch files (audit JSONL) are created
only under the group's `scratch/` directory, never `/tmp`.

## Coverage map

| File | Tests | Core function(s) traced |
|---|---:|---|
| `test_access.py` | 17 | 9 Access control & API keys — exact permission matrix for admin/member/viewer (admin = all eight actions; member = {read, registry_write, invoke, eval_run, usage_read}; viewer = {read, usage_read}), `permissions_for()`, `can()`, `require()`, unknown role/action denied; **[L3]** `TestAuditorRole` (6 tests): auditor = {audit_read} only (AC-5) |
| `test_audit.py` | 12 | 10 Audit log — entry keys `ts, actor, action, target, details` **[L3: plus `seq, prev_hash, hash`]**, append-only, JSONL file + reload on construction, and the store recording each mutation action (`model_register`, `template_register`, `key_create`, `quota_set`, `session_create`, `invoke`, `policy_add`, `policy_remove`, `eval_dataset_create`, `eval_run`, `model_status`) |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash fields, genesis `prev_hash`, canonical-hash recomputation, link integrity, `verify_chain()`, JSONL round-trip + edited-line detection, negative control #2, `GET /audit/verify`, auditor HTTP reach (AC-5) |
| `test_audit_failure.py` | 7 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, chain intact after failure, store-level rollback (register / invoke / status: no object, no id consumed, no state move), service-level non-success |
| `test_audit_query.py` | 12 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until, inclusive bounds, composition), `GET /audit` parameter pass-through, member denied |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, unknown-user lockout, per-user isolation, success resets counter, lock expiry |
| `test_registry.py` | 19 | 1 Model registry + 2 Prompt template registry — shapes/provenance, `mdl-`/`tpl-` id sequences, auto-incrementing versions per name, explicit duplicate (name, version) → `ValidationError`, responder/config validation (template requires `config["template"]`; rules requires `{match, response}` pairs + `default`), `get_*` highest-version selection, sorted lists, `set_model_status`, viewer write denials, failed ops consume no ids |
| `test_keys_quotas.py` | 18 | 9 Access control & API keys + 4 Usage metering & quotas — secret shown only at creation, store keeps only the SHA-256 digest (and the secret is never audited), `authenticate_key`, owner-scoped key lists without `secret`/`secret_hash`, owner-or-admin key creation, quota set/get/replace + positive-integer validation + admin-only set, current-month `usage_for` aggregation, quota pre-check (strict "would exceed", exact-limit allowed, charged to the key's owner) |
| `test_gateway.py` | 18 | 3 Gateway & reference responder + 4 pinned estimator — `estimate_tokens` formula (`0` for empty, else `(len+3)//4`), exact `REFERENCE_NOTICE` text, echo/template/rules responders, invoke record shape with `reference_stub: true`, version routing, deprecated-model refusal, key/session/template steps (2–4), stub audit details `{model, total_tokens}`, viewer denial |
| `test_policy.py` | 16 | 6 Policy guardrails — rule shape/`rule-` ids, scope/kind/regex-compile validation, creation-order evaluation (first match blocks), term (case-insensitive substring) and pattern (regex search) matching, input/output/both scoping, `blocked_input` and `blocked_output` records with pinned usage, `PolicyBlocked.request_id`, `invoke_blocked` audit details `{stage, rule_id}`, blocked records counted in usage, admin-only `policy_write` |
| `test_records.py` | 15 | 5 Conversation & request records — session shape/`ses-` ids, owner-or-admin session reads, scoped chronological session/request lists, turns appended on completion only (never on a block), request-record operational metadata, and zero-persistence mode: records and turns carry `prompt`/`output` as `None` plus `content_withheld: true` with metadata stored in full (normal mode carries no `content_withheld` key) |
| `test_eval.py` | 13 | 7 Evaluation harness — dataset validation + sequential `case-1…` ids, exact (strip-compared) and contains (case-insensitive) scoring, rubric criteria (all must pass), `score = passed/total` as a float, runs exercise the responder directly (no request record, no metering, no quota/policy effect), `eval_run` audit, creator-or-admin run reads, datasets/runs stored by design even in zero-persistence mode |
| `test_service.py` | 19 | 8 API access — live HTTP server: health without auth, 401 unknown user / role mismatch, 403 viewer actions, 404 unknown model/path, 400 invalid input, 422 policy-blocked completion, 429 quota-exceeded completion, full flows (models/templates/keys/quotas/completions/sessions/requests/usage/policy rules + delete/eval datasets + runs/audit), secret-once over HTTP, `audit_read` admin-only, denied attempts (401/403/422/429) audited with the `:denied` suffix, no stack traces |
| `test_main_cli.py` | 4 | `python -m aigateway serve` subprocess with demo users alice/bob/carol, including the `--zero-persistence` flag end-to-end over HTTP and the no-command help path; **[L3]** +1: dana=auditor (AC-5) and `--max-failed-logins` / `--lockout-seconds` (AC-7) |
| `test_negative_control.py` | 2 | Negative control #1 (below), unchanged from Group 9 |
| `aigateway_helpers.py` | — | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OTHER_MEMBER, **[L3]** AUDITOR), `make_store()` building an AIGatewayStore + AuditLog + an ADMIN-registered echo model, template/rules model helpers, and scratch-dir helpers confined to the group's `scratch/` |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 4 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (no object, no id consumed), service propagates | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (7 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only | AC-5 | `access.py`, `__main__.py` (demo user `dana=auditor`) | `test_access.py` (6 tests), `test_audit_chain.py`, `test_audit_query.py`, `test_main_cli.py` |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 L2 core functions keep their Group 9 coverage (see the file
table); the L3 public API contract is the L2 contract plus exactly
the uplifts above.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 9): the mutant
   policy check that treats **every** text as clean (always returns
   "no match"). The traced claim, named in the module's docstrings,
   is that the policy gate is the gateway's guardrail enforcement
   point (invoke step 6). For the canonical case (a prompt containing
   the blocked term `badword`) the tests assert three things: the
   canonical expectation (`PolicyBlocked` from the real
   implementation, exactly one stored `blocked_input` record, nothing
   completed, an `invoke_blocked` audit entry naming the rule), that
   the mutant gate would NOT raise (it waves the blocked prompt
   through as "allowed"), and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails. The module does **not**
   patch the real `src/` policy evaluation itself; that drill is
   performed live in the mutation record below.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**
   [L3]: a clean log verifies `(True, None)`; mutating a stored entry
   in place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field and a rewritten `prev_hash`, and an edited
   JSONL line after reload.

## Mutation verification

Both drills performed on this build (2026-10-25), for real:

**(a) Policy wave-through (negative control #1, live counterpart).**
The policy evaluation in `AIGatewayStore._first_policy_match`
(`src/aigateway/store.py`) — the gateway's single policy-evaluation
point, invoked for both the input and output stages — was patched to
`return None` as its first statement: the exact live counterpart of
the mutant in `test_negative_control.py`, treating every text as
clean and waving every blocked invocation through.

- Pre-mutation `src/aigateway/store.py` SHA-256:
  `2c71ff5569b584bcd5e20804cbf0e4d48e18d98f98f948729e79f5ed9c515031`
  (a copy is kept at `scratch/store.py.premutation`).
- Suite under mutation: **193 tests ran, 14 failed** — the same 14,
  in the same distribution, as the Group 9 parent drill: 8 in
  test_policy (input term block, regex pattern rule, output block
  with withheld output, first-match ordering, both-scope blocking,
  blocked record + exception request_id, blocked audit entry,
  blocked usage accounting), 2 in test_negative_control (the
  canonical expectation and the mutant-gate demonstration), 1 in
  test_gateway (a policy block is not a completion), 1 in test_service
  (HTTP 422 for a policy-blocked completion), and 2 in test_records
  (blocked record content withholding under zero-persistence, no
  session turn appended for a blocked invoke). None of the 40 uplift
  tests depends on policy outcomes, so none failed — as expected.
- `store.py` was then restored from the pre-mutation copy; SHA-256
  verified identical to the pre-mutation hash
  (`2c71ff55…c515031`, `cmp` clean); suite re-run: **193 tests, OK**.
  The suite catches this defect class; the negative control is not
  decorative.

**(b) Audit tamper (negative control #2).**
`test_audit_chain.py::TestVerifyChain::test_negative_control_2_mutated_entry_fails_at_index_1`
was run explicitly against this build and passes: the clean
4-entry log verifies `(True, None)`; after the in-place mutation
`log._entries[1]["actor"] = "mallory"`, `verify_chain()` returns
`(False, 1)` — the tamper is localized at the exact mutated index,
not merely detected. The full `test_audit_chain` module (15 tests,
including stripped-hash, broken-link, and edited-JSONL-after-reload
companions) is green in the suite run above.

## Group 9 test adaptations (complete list)

Every copied Group 9 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — one exact key-set assertion extended.**
   `test_record_and_entries_roundtrip` asserted audit entries carry
   *exactly* `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertion now
   requires the original five keys plus the three chain keys. No
   other audit assertions changed — the original keys and values are
   unchanged.
2. **`test_access.py` — additive only.** The module docstring names
   the auditor role; a new `TestAuditorRole` class (6 tests) pins
   `auditor = {audit_read}` (AC-5). All existing per-role permission
   assertions are unchanged (existing roles' permissions did not
   move).
3. **`aigateway_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user. No
   existing helper, user, or fixture changed; `test_service.py`
   (which consumes the registry) needed no edits — its per-username
   authentication-failure counts stay below the new default lockout
   threshold, so no lockout trips. Authorization (403) failures do
   not count toward AC-7, which tracks authentication failures only.
4. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags and
   the dana demo user; the original CLI tests are unchanged apart
   from the module docstring's demo-user line.

No other Group 9 test file was modified (`test_registry.py`,
`test_keys_quotas.py`, `test_gateway.py`, `test_policy.py`,
`test_records.py`, `test_eval.py`, `test_service.py`,
`test_negative_control.py` are byte-identical to Group 9).

## Interpretation notes

Inherited from Group 9 and still in force:

- `usage_for`'s `month` is the current UTC month as `YYYY-MM`, and
  usage aggregates the records' `total_tokens` for the effective
  owner (the key's owner when a key is used, else the actor).
- List endpoints over HTTP wrap their payload (`{"models": [...]}`,
  `{"templates": [...]}`, `{"keys": [...]}`, `{"requests": [...]}`,
  `{"sessions": [...]}`, `{"rules": [...]}`, `{"datasets": [...]}`),
  mirroring the sibling Collaboration build; `/audit` is pinned by
  the contract to `{"entries": [...]}`.
- Statuses the contract does not pin are 200: `POST /quotas`,
  `POST /models/{name}/versions/{v}/status`, and
  `DELETE /policy/rules/{id}`. Creation endpoints the contract does
  pin to 201 are asserted as 201.
- `run_eval` refuses a deprecated model with `ValidationError`, by
  the same "deprecated models refuse requests" rule the contract
  pins for the gateway (Core function 1); the contract does not
  state this case for eval explicitly.
- The service records `audit_read` before reading the entries, so a
  successful `GET /audit` response's trail includes that read itself.
- A plain string actor carries identity but no role (the sibling
  build's `_maybe_require` convention): role enforcement applies to
  User-like actors, which is what the service layer always passes.

L3-specific notes:

- `GET /audit` keeps the Group 9 audit-first ordering above even when
  filters are passed (the L3 reference builds compute the filtered
  trail before appending their `audit_read` entry): the filters are
  the uplift, the ordering is this build's pinned L2 behavior, and
  the inherited `test_service.py` audit test depends on it. Filtered
  responses therefore include the request's own `audit_read` entry
  when it matches the filters (it is appended after all prior
  entries, so prefix assertions on a seeded trail are stable).
- `GET /audit/verify` follows the L3 reference ordering instead (no
  L2 behavior existed for it): the count and verification are read
  *before* the endpoint's own `audit_read` entry is appended, and
  the endpoint test asserts against the pre-request length.
- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic. Pinning `ts` after
  recording breaks those entries' hash chains *by construction* —
  chain integrity is asserted in `test_audit_chain.py` on unpinned
  logs, and the two concerns are never mixed in one fixture.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform. All such files live under the group's `scratch/`
  directory via `aigateway_helpers.make_scratch_dir()`.
- **Lockout tests use fresh servers per test** (`test_lockout.py`):
  AC-7 state lives on the server instance, so counter leakage
  between tests would be a harness artifact, not behavior. Expiry is
  tested with a real 1-second lock and a 1.2-second wait — the
  suite's only sleep.
- Over HTTP an `AuditWriteError` surfaces as 500 `audit write
  failed` (the collaboration-l3 mapping), not the generic 400 for
  other `AIGatewayError`s: at the service layer the audit failure is
  itself the reportable failure. The store-level error type and
  rollback are what `test_audit_failure.py` pins.
