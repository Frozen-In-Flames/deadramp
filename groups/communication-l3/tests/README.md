# Tests — Communication L3 merged build (CMMC L3-adjacent / FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core function /
spec claim / control family it traces to.

This suite **extends the shipped Group 11 (Communication L2) suite**:
the L2 tests (82 tests / 13 files) were copied and pass except for the
minimal adaptations listed below, and new files cover the High-baseline
uplifts. Per the Merge Rule, the merged fork inherits the higher tier
(High) in full while reusing the Group 11 code wherever functions
overlap.

## Run

```bash
cd groups/communication-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 138 tests
```

Status at delivery: **138 tests, OK** (93 tests in the 13 inherited
L2 files — the original 82 plus 11 tests added inside those files by
the adaptations below — and 45 tests in 6 new uplift files). (Run
exactly as above: helpers are imported as a top-level module from the
tests directory and `tests/__init__.py` is empty by design, so
package-mode discovery with `-t .` is not the supported entry point
for this group.)

Note on repeatability: the first full run of the finished suite
showed one transient failure in
`test_auditor.TestAuditorOverHttp.test_auditor_operational_gets_are_403`;
that test then passed standalone and the full suite passed on five
consecutive subsequent full runs (including the post-drill restore
run). No code was changed to work around it.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 16 | Access control (RBAC) — exact permission matrix for admin/operator/viewer/**auditor**, `permissions_for()`, `can()`, `require()`, unknown role/action denied; **AC-5**: auditor role = `{audit_read}` only (6 new/adapted) |
| `test_audit.py` | 11 | Append-only audit log — entry keys (superset, see adaptations), User actor normalised to name, append-only/copies, basic chain fields (`seq`/`prev_hash`/`hash`), JSONL persistence + reload on construction and reload-then-`verify_chain()` (in group `scratch/`), store recording each mutation action, failed ops record nothing |
| `test_audit_chain.py` | 9 | **AU-9 / AU-3** hash chain: seq/prev_hash/hash, canonical-JSON hash recomputation, links, `verify_chain()`, in-place mutation localised at the exact index, deletion detected, stripped hash field detected, JSONL round-trip + file-edit detection after reload |
| `test_audit_failure.py` | 5 | **AU-5** fail closed: `AuditWriteError` rollback in `record()`, store `create_contact` commits nothing and consumes no id (next healthy op gets `ct-1`), service returns 500 `{"error": "audit write failed"}` exactly |
| `test_audit_query.py` | 12 | **AU-7 / AU-6** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until, inclusive bounds, combined), `GET /audit` query-param passthrough incl. auditor use |
| `test_audit_verify.py` | 5 | **AU-9 / AU-6** `GET /audit/verify`: exact shape `{"ok", "entries", "first_bad_index"}`, entries counted **before** this read's own `audit_read` entry, tampered chain reported at the exact index, 200 for admin+auditor / 403 for operator+viewer |
| `test_auditor.py` | 7 | **AC-5** auditor role end to end: matrix exactness, store-level denials of every operational read/write, service-level dana 200 on `/audit` and `/audit/verify`, 403 on operational GET and POST endpoints |
| `test_lockout.py` | 7 | **AC-7** unsuccessful logon lockout over HTTP: threshold (3), locked correct-role attempt → 403 + `auth:locked` audit, unknown usernames lock, per-user scope, success resets counter, lock expiry (small `lockout_seconds`), `/health` stays reachable |
| `test_contacts.py` | 7 | Directory contacts — creation shape/provenance, `ct-` ids, get/list sorted by id, validation (empty name/addresses, bad kind, empty address), viewer write denied, failed ops consume no ids |
| `test_groups.py` | 5 | Directory groups — `grp-` creation, add member, duplicate membership → `ValidationError`, unknown ids → `NotFoundError`, `list_group_members` returns contact dicts |
| `test_channels.py` | 5 | Channels — all four known kinds {email, sms, voice, push}, `ch-` ids, invalid kind, `channel_write` admin-only, `set_channel_enabled` |
| `test_templates.py` | 6 | Templates — `tpl-` creation, `render_template` substitutes every placeholder, missing variable → `ValidationError`, extra variables ignored |
| `test_messages.py` | 9 | Message composition + delivery records — literal and template compose, recipient union deduped order-stable, default kind order email,sms,voice,push, `skipped_recipients`, zero-deliveries → `ValidationError` with no message/id consumed, malformed `send_at` |
| `test_dispatch.py` | 8 | Dispatch with receipts + scheduling — reference-transport receipt labelled `reference_transport: True`, disabled/absent channel → `failed`/`no_enabled_channel`, `send_at` gate (`dispatch_due` skips future, explicit `now` string/datetime, `dispatch_message` future → `ValidationError`), viewer cannot dispatch, no re-dispatch |
| `test_ack.py` | 5 | Acknowledgement tracking — ack requires `delivered` status and `require_ack=True`, `ack_status` totals/pending, viewer denied, unknown ids |
| `test_search.py` | 6 | Immutable records + search — literal case-insensitive substring over contacts (name + addresses), messages (subject + body), deliveries (address); literal not regex; shape `{contacts, messages, deliveries}` |
| `test_service.py` | 8 | REST API — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer write + channel_write for operator, full flow (contact → group → channel → template → message → dispatch-due → ack → search → audit), `audit_read` admin+auditor (operator still denied), denied attempts audited with `:denied`, 400/404 envelopes |
| `test_main_cli.py` | 3 | `python -m comm serve` subprocess with demo users alice/bob/carol; **+2 new**: dana=auditor in the startup line `"(demo users: alice=admin, bob=operator, carol=viewer, dana=auditor)"`, `--max-failed-logins` / `--lockout-seconds` accepted (parse-level defaults 3/300) and plumbed through (bob locks after 2 bad-role attempts) |
| `test_negative_control.py` | 4 | Negative controls #1 and #2 (below) |
| `comm_helpers.py` | — | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER/AUDITOR), `USERS` registry incl. dana, `fresh_store()`, and `make_store()` building a CommStore + AuditLog + a contact + a group containing it + an enabled email channel (created by ADMIN) |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (9 tests), chain fields + reload-then-verify in `test_audit.py`, tamper report in `test_audit_verify.py` |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read), entries counted before its own `audit_read` entry | AU-9, AU-6 | `service.py` | `test_audit_verify.py` (5 tests), auditor use in `test_auditor.py` |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7, AU-6 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 4 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError` (in `comm.errors`); store is audit-before-commit (nothing changes, no id consumed); service surfaces 500 `{"error": "audit write failed"}` | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (5 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` (service `USERS` registry incl. dana) | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py` (6 tests), `test_auditor.py` (7 tests), `test_service.py`, `test_main_cli.py` |
| Unsuccessful logon lockout: `make_server(..., max_failures=3, lockout_seconds=300)`; per-username consecutive failures; locked attempts (even correct role) → 403 + `auth:locked` audit; success resets; expired lock clears | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (7 tests), `test_main_cli.py` |

## Negative controls

1. **`test_negative_control.py::TestNegativeControlMutantDispatch`**
   (kept from Group 11): a `CommStore` subclass (`MutantCommStore`)
   whose `_first_enabled_channel` always returns a fake enabled
   channel — the enabled-channel check is skipped. The traced claim
   is that **dispatch honors the send gate**: a disabled or absent
   channel must fail the delivery with
   `failure_reason='no_enabled_channel'`, and a viewer must not
   dispatch. For each canonical case (disabled channel, absent
   channel, viewer dispatch) the test asserts three things: the
   canonical expectation (failed delivery / `PermissionDenied` from
   the real implementation, with the delivery staying queued for the
   viewer case), that the mutant would NOT produce that expectation
   (it delivers anyway / waves the viewer through its gate), and —
   via a literal `assertRaises(AssertionError)` — that treating the
   mutant's outcome as the expected outcome fails.
2. **`test_negative_control.py::TestNegativeControlAuditTamper`**
   (new in L3): a stored audit entry mutated in place (its actor
   changed to `"mallory"`) must leave `verify_chain() ==
   (False, that entry's index)` — the canonical integrity
   expectation **rejects** the tampered log — while a naive mutant
   verifier that always returns `(True, None)` accepts it, shown via
   the same `assertRaises(AssertionError)` pattern. Companion
   coverage in `test_audit_chain.py` localises an in-place mutation
   at the exact index, detects a deleted entry and a stripped hash
   field, and detects an edited JSONL line after reload; the same
   tamper is reported over HTTP by `test_audit_verify.py`.

## Mutation verification

Both drills were performed by the tests worker (2026-10-25);
pre-mutation backups and hashes live in `../scratch/` (drill logs in
`../scratch/tests-worker/`).

**Drill 1 (send gate).** `src/comm/store.py` was copied to
`scratch/store.py.bak` (SHA-256
`bfc7877c7a38dae178850b07cccbb1df67efb1ef78e5bdad054be1139125f45d`)
and the send-gate line `if channel is None:` in
`CommStore._dispatch_deliveries` was patched to `if False:`, the
exact live counterpart of the mutant in `test_negative_control.py`,
so dispatch delivered even with a disabled or absent channel. The
full suite was run: **138 tests ran, 4 failed** —

- `test_dispatch.TestDispatch.test_dispatch_due_absent_channel_fails`
- `test_dispatch.TestDispatch.test_dispatch_due_no_enabled_channel_fails`
- `test_negative_control.TestNegativeControlMutantDispatch.test_absent_channel_fails_canonical_but_mutant_delivers`
- `test_negative_control.TestNegativeControlMutantDispatch.test_disabled_channel_fails_canonical_but_mutant_delivers`

`store.py` was then restored from the backup — SHA-256 verified
identical to the pre-mutation hash above.

**Drill 2 (audit hash).** `src/comm/audit.py` was copied to
`scratch/audit.py.bak` (SHA-256
`2c719311f3b8f4620ebe531eb181cc4527de7dcd05596ac704d0343fcf4e7bf8`)
and `_entry_hash` was patched to return the constant `"0" * 64`. The
full suite was run: **138 tests ran, 5 failed** —

- `test_audit_chain.TestHashChainFields.test_hash_is_sha256_of_canonical_json`
- `test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_detected_after_reload_at_right_index`
- `test_audit_chain.TestVerifyChain.test_verify_chain_localizes_in_place_mutation`
- `test_audit_verify.TestAuditVerifyEndpoint.test_verify_reports_tampered_chain_at_exact_index`
- `test_negative_control.TestNegativeControlAuditTamper.test_tampered_entry_is_rejected_by_canonical_verifier`

Honest note (mirroring collaboration-l3's drill record): the basic
seq/`prev_hash`-linkage assertions in `test_audit.py` and
`test_audit_chain.py`'s linkage test still **hold** under a constant
hash — every `prev_hash` is `"0"*64` and every `hash` is `"0"*64`, so
the links line up trivially; clean-log verification, deletion
detection (a `seq` mismatch), and stripped-field detection also still
pass, since they do not depend on the hash value. The defect is
caught by the canonical-hash recomputation, the in-place mutation
localisation, the edited-JSONL detection, the `/audit/verify`
tamper report, and the audit-tamper negative control — which is
exactly those tests' job.

After Drill 2, `audit.py` was restored from the backup — SHA-256
verified identical to the pre-mutation hash above — and the full
suite was re-run: **138 tests, OK**. The suite catches both defect
classes; neither negative control is decorative.

## Group 11 (L2) test adaptations (complete list)

Every copied Group 11 test passes as-is except these deliberate,
uplift-driven changes (verified by diff: the other inherited files —
`test_ack.py`, `test_channels.py`, `test_contacts.py`,
`test_dispatch.py`, `test_groups.py`, `test_messages.py`,
`test_search.py`, `test_templates.py`, and `__init__.py` — are
byte-identical to Group 11):

1. **`comm_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS`, mirroring the new demo user. Header docstring
   updated to name the L3 group and dana. No existing helper, user,
   or fixture changed.
2. **`test_access.py` — role-set extended, auditor tests added.**
   `test_roles_exact` now expects
   `{admin, operator, viewer, auditor}`; `AUDITOR_SET = {"audit_read"}`
   was added; `test_auditor_permissions_exact` added;
   `test_permissions_for_matches` and `test_can_matrix` extended to
   the auditor; a new `TestAuditorRole` class (5 tests, AC-5) was
   added. All existing per-role permission assertions are unchanged
   (existing roles' permissions did not move: admin = all 12 actions
   incl. `audit_read`; operator = reads + writes, NO `audit_read`;
   viewer = 4 reads).
3. **`test_audit.py` — exact key-set assertion relaxed to a
   superset, plus chain coverage.** `test_record_roundtrip` now
   requires `{ts, actor, action, target, details, seq, prev_hash,
   hash}` ⊆ entry keys (was: exact equality with the five L2 keys)
   and asserts the genesis chain fields; the JSONL reload test also
   asserts the chain keys survive reload. Two tests were added:
   `test_chain_fields_seq_increments_and_links` and
   `test_jsonl_reload_then_verify_chain`. No other audit assertions
   changed.
4. **`test_service.py` — audit_read is now admin+auditor.** A `DANA`
   header constant was added and
   `test_audit_admin_only` became
   `test_audit_admin_and_auditor_only`: operator (bob) and viewer
   (carol) are still 403 on `GET /audit`, admin (alice) is 200, and
   auditor (dana) is now also 200. Module docstring updated to the
   4-user registry. Nothing else changed; its auth-failure counts
   per username stay below the new default lockout threshold, so no
   lockout trips.
5. **`test_main_cli.py` — additive uplift class.** The module
   docstring now includes `dana=auditor`; a new
   `TestCommandLineUplifts` class (2 tests) checks the startup-line
   substring `"(demo users: alice=admin, bob=operator, carol=viewer,
   dana=auditor)"` (also asserting dana answers 200 on `/audit` and
   that `--max-failed-logins 2` locks bob) and the AC-7 CLI flags at
   parse level (defaults 3/300). The original CLI test is unchanged.
6. **`test_negative_control.py` — second control added.** The L2
   send-gate mutant, its gate, and its three tests are unchanged; a
   new audit-tamper control (Negative controls #2, above), its
   `mutant_verify_chain` naive verifier, and a docstring paragraph
   naming it were added.

## Interpretation notes

Inherited from Group 11 and still in force:

- Audit `details` defaults are accepted as `None` or `{}`.
- Over HTTP, auth failures are asserted as exactly 401 per the
  contract ("unknown user or mismatched role → 401"); creation
  endpoints pinned to 201 are asserted as 201.
- Store-level permission enforcement applies only when the actor is
  a User-like object (has a `role`); plain-string actors carry
  identity only, and enforcement for them is the service layer's job.

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic (pinning `ts` after
  `record()` deliberately does not recompute hashes; `query` does
  not verify the chain).
- `GET /audit/verify`'s `entries` count is read **before** the
  verify's own `audit_read` entry is recorded, so immediately after
  a verify call the log holds `entries + 1` entries (the verify's
  own). `GET /audit` has the same shape: the returned entries are
  the trail as it stood before that read's own `audit_read` entry
  was appended.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform. All scratch for these tests lives in the group's
  `scratch/` directory (never `/tmp`).
- Lockout state is scoped to one server instance: `test_lockout.py`
  builds a fresh server per test so failure counters never leak
  between tests, and the expiry test uses `lockout_seconds=0.3`
  with a 0.5 s sleep rather than mocking the clock.

## Remainder addition — unit addition:communication-l3 (Oct 31, 2026)

One fork appended to `specs/specs.json` (6 → 7 sheets): GovSlack
(`FR2230252267`, Slack Technologies, FedRAMP High / Certified).
Full record in [`../ADDENDUM.md`](../ADDENDUM.md).

| File | Tests | Covers |
|---|---:|---|
| `test_additions.py` | 11 | Addition spec integrity: sheet count/order + membership vs `../../remainder.json`, registry fields as published, literal claim table (exactly 1 claim — `messaging`), the 20-family zero-claim set, group totals (7 forks / 12 claims / 6 claiming), verbatim evidence + description byte-equal to the cached record, census citations 2/2, near-miss token pins; substrate cases: group-addressed messaging flow (compose → dispatch with `reference_transport` receipt → ack), send gate with no enabled channel, High baseline (chain verifies; auditor cannot compose) |

**Status: 149 tests, OK** (138 shipped + 11 additions).

**Drill re-run (Drill 1, send gate).** The core is unchanged, so
the group's signature drill was re-run in this tree:
`src/comm/store.py` was copied to
`scratch/store.py.premutation_additions` and the send-gate line in
`CommStore._dispatch_deliveries` (`if channel is None:`, the exact
line the shipped drill record names) was patched to `if False:`.
The full suite ran: **149 tests, exactly 5 failed** — the shipped
drill's 4 (`test_dispatch_due_absent_channel_fails`,
`test_dispatch_due_no_enabled_channel_fails`, and the two
negative-control canonical cases) plus exactly 1 from the
additions module
(`test_additions.TestAdditionsSubstrate.test_govslack_send_gate_no_enabled_channel`),
tripping exactly as designed. `store.py` was restored from the
pre-mutation copy — SHA-256 verified identical to the shipped
hash (`bfc7877c…`) — and the suite re-ran green. Raw output:
`scratch/additions_mutation_run.txt`. Drill 2 (audit hash) was
not re-run: the addition changes no audit code or audit-facing
behavior, and its shipped record stands.
