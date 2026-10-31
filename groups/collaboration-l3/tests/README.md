# Tests — Collaboration L3 merged build (CMMC L3-adjacent / FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core function /
control family it traces to.

This suite **extends the shipped Group 2 (Collaboration L2) suite**:
the L2 tests were copied and pass except for the minimal adaptations
listed below, and new files cover the High-baseline uplifts. Per the
Merge Rule, the merged fork inherits the higher tier (High) in full
while reusing the Group 2 code (Apache-2.0, ours) wherever functions
overlap.

## Run

```bash
cd groups/collaboration-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 251 tests
```

Status at delivery: **239 tests, OK** (192 inherited from Group 2,
47 added for the High uplifts). The remainder addition
(`addition:collaboration-l3`, Microsoft 365 GCC) added
`test_additions.py` (12 tests): **251 tests, OK** — see
`../ADDENDUM.md` and the additions drill record under Mutation
verification below. (Run exactly as above: helpers are
imported as a top-level module from the tests directory and
`tests/__init__.py` is empty by design, so package-mode discovery
with `-t .` is not the supported entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 22 | 10 Access control — exact permission matrix, `permissions_for()`, `can()`, `require()`, unknown role/action denied; **AC-5**: auditor role = `{audit_read}` only (5 new) |
| `test_audit.py` | 14 | 11 Audit log — entry keys (superset, see adaptations), append-only, JSONL file + reload, basic chain fields, the store recording each mutation action |
| `test_audit_chain.py` | 9 | **AU-9 / AU-3** hash chain: seq/prev_hash/hash, canonical-JSON hash recomputation, links, `verify_chain()`, in-place mutation localised, deletion detected, JSONL round-trip + file-edit detection after reload |
| `test_audit_failure.py` | 5 | **AU-5** fail closed: `AuditWriteError` rollback in `record()`, store `create_workspace` commits nothing and consumes no id, service returns 500 `{"error": "audit write failed"}` |
| `test_audit_query.py` | 12 | **AU-7 / AU-6** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until, combined), `GET /audit` query params incl. auditor use |
| `test_lockout.py` | 7 | **AC-7** unsuccessful logon lockout over HTTP: threshold (3), locked correct-role attempt → 403 + `auth:locked` audit, unknown usernames lock, per-user scope, success resets counter, lock expiry, `/health` stays reachable |
| `test_workspaces.py` | 20 | 1 Workspaces — creation shape/provenance, `ws-` id sequence, list visibility, owner-or-admin `add_member`, duplicate add → `ValidationError`, non-member get → `PermissionDenied`, failed ops consume no ids |
| `test_messaging.py` | 25 | 2 Messaging & chat — channels, post shape, same-channel threading (cross-channel parent → `ValidationError`), chronological list + limit, mentions notifying members only, never the author |
| `test_files.py` | 19 | 3 File sharing — versioned records, `sha256` = hashlib of the UTF-8 content, `size_bytes`, re-share → next version, `get_file` returns content, other members notified |
| `test_calendar.py` | 16 | 4 Calendaring — event shape, `end <= start` → `ValidationError`, malformed datetimes → `ValidationError`, member attendees notified, non-member attendees not |
| `test_presence.py` | 15 | 5 Presence — each of available/busy/dnd/offline, invalid status → `ValidationError`, self-or-admin enforcement, unset → `NotFoundError` |
| `test_boards.py` | 19 | 6 Whiteboards — boards, positioned cards, non-numeric x/y → `ValidationError`, move card, per-board scoping |
| `test_search.py` | 13 | 7 Search — literal case-insensitive substring over messages/files/events/cards, and the scoping guarantee: results never leak another workspace's objects |
| `test_notifications.py` | 11 | 8 Notifications — per-user queue oldest-first, feed kinds (mention/file_share/event_invite), `mark_read` by owner or admin only |
| `test_service.py` | 24 | 9 API access — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer posting, full flow (workspace → channel → message → file → event → search → notifications → audit), denied attempts audited with `:denied`; **AC-5/AU-9 (5 new)**: dana reads `/audit`, cannot list/create workspaces, `GET /audit/verify` 200 for dana / 403 for bob |
| `test_main_cli.py` | 3 | `python -m collab serve` subprocess with demo users alice/bob/carol; **+2 new**: dana=auditor in the startup line `"(demo users: alice=admin, bob=member, carol=viewer, dana=auditor)"`, `--max-failed-logins` / `--lockout-seconds` accepted (parse-level defaults 3/300) and plumbed through |
| `test_negative_control.py` | 5 | Negative controls #1 and #2 (below) |
| `test_additions.py` | 12 | Remainder addition `addition:collaboration-l3` (MSO365MTA): spec integrity (membership vs `remainder.json`, literal claim table — 1 claim, `messaging_chat`; the 20-family unclaimed set; verbatim evidence; description = cached source; the census citation, which is also the claim's evidence; near-miss pins; source-as-published registry fields) + substrate at the High baseline (mention notification, opaque file list view, hash chain verifies + audit reduction query; membership-boundary post case — the additions case that trips under Drill A) |
| `collab_helpers.py` | — | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/AUDITOR/OUTSIDER), `make_store()` building a CollabStore + AuditLog + a workspace owned by MEMBER with VIEWER added, and sample message/file/event/board helpers; L3 adds the `AUDITOR` user / `dana` registry entry |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (9 tests), chain fields in `test_audit.py` |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_service.py` (auditor/member endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7, AU-6 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 4 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store is audit-before-commit (nothing changes, no id consumed); service surfaces 500 `{"error": "audit write failed"}` | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (5 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `__main__.py` | `test_access.py` (5 tests), `test_service.py`, `test_main_cli.py` |
| Unsuccessful logon lockout: `make_server(..., max_failures=3, lockout_seconds=300)`; locked attempts → 403 + `auth:locked` audit; success resets; expired lock self-clears | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (7 tests), `test_main_cli.py` |

## Negative controls

1. **`test_negative_control.py::TestNegativeControlMutantMembership`**
   (kept exactly from Group 2): a membership check that treats
   **every** actor as a workspace member. The traced claim is that
   workspace membership is the AC-3 access-enforcement boundary. For
   each canonical case (non-member `post_message`, non-member
   `share_file`, non-member `list_messages`, non-member `search`)
   the test asserts three things: the canonical expectation
   (`PermissionDenied` from the real implementation, with nothing
   stored), that the mutant gate would NOT raise (it waves the
   non-member through), and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails.
2. **`test_negative_control.py::TestNegativeControlAuditTamper`**
   (new in L3, mirroring Group 3): a stored audit entry mutated in
   place (its actor changed to `"mallory"`) must leave
   `verify_chain() == (False, that entry's index)` — the canonical
   integrity expectation **rejects** the tampered log — while a naive
   mutant verifier that always returns `(True, None)` accepts it,
   shown via the same `assertRaises(AssertionError)` pattern.
   Companion coverage in `test_audit_chain.py` localises an in-place
   mutation, detects a deleted entry and a stripped hash field, and
   detects an edited JSONL line after reload.

## Mutation verification

Both drills were performed by the tests worker (2026-10-25);
backups and hashes live in `../scratch/`.

**Drill A (membership, the Group 2 drill).** `src/collab/store.py`
was copied to `scratch/store.py.bak` (SHA-256
`bd8941693f91df9705340102a0932f17463583dfaba785ae9222528b79aa880c`)
and the membership condition in `_require_workspace_access` was
patched to `if False:`, waving every non-member through. The full
suite was run: **239 tests ran, 14 failed**. The failures span 8
files: the 4 membership negative-control tests in
`test_negative_control.py`, plus non-member cases in
`test_boards.py` (2), `test_messaging.py` (2),
`test_workspaces.py` (2), `test_calendar.py` (1),
`test_files.py` (1), `test_search.py` (1) and `test_service.py` (1,
the HTTP 403 case). `store.py` was then restored from the backup —
SHA-256 verified identical to the pre-mutation hash above — and the
suite re-run: **239 tests, OK**.

**Drill B (audit hash).** `src/collab/audit.py` was copied to
`scratch/audit.py.bak` (SHA-256
`c7e586468e71038f3dfbf57d7ff6f16cf015638b0053c42280189fb9679e060f`)
and `_entry_hash` was patched to return the constant `"0" * 64`.
The audit-focused files were run: **28 tests ran, 4 failed** —
`test_audit_chain.py` 9 tests / 3 failures (canonical-hash
recomputation, in-place mutation localisation, edited-JSONL-line
detection), `test_negative_control.py` 5 tests / 1 failure (the
audit-tamper control), and `test_audit.py` 14 tests / 0 failures
(its basic seq/linkage assertions hold even under a constant hash;
the defect is caught by the chain and negative-control files, which
is exactly their job). `audit.py` was restored from the backup —
SHA-256 verified identical — and the full suite re-run:
**239 tests, OK**.

The suite catches both defect classes; neither negative control is
decorative.

**Additions drill re-run (remainder unit
`addition:collaboration-l3`).** The core is unchanged by the
addition, so Drill A was re-run in this tree: `store.py` was
copied to `../scratch/store.py.premutation_additions` and the
membership condition in `_require_workspace_access` was patched
to `if False:` — the exact mutant of Drill A. The full suite ran:
**251 tests, 15 failures** — Drill A's original 14 plus 1 from
the new additions module (`test_additions.py`'s M365
membership-boundary post case), tripping exactly as designed.
`store.py` was restored from the pre-mutation copy — SHA-256
verified identical to the shipped hash (`bd894169…`) — the whole
`src/` tree was re-verified against the pre-addition hash list in
`../scratch/`, and the suite re-ran: **251 tests, OK**. Raw
output: `../scratch/additions_mutation_run.txt`.

## Group 2 test adaptations (complete list)

Every copied Group 2 test passes as-is except these deliberate,
uplift-driven changes:

1. **`collab_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user. No
   existing helper, user, or fixture changed.
2. **`test_access.py` — role-set test extended, auditor class
   added.** `test_roles_are_exactly_admin_member_viewer` became
   `test_roles_are_exactly_admin_member_viewer_auditor`: the uplift
   adds the `auditor` role to `PERMISSIONS`. All existing per-role
   permission assertions are unchanged (existing roles' permissions
   did not move). Five auditor tests were added in a new
   `TestAuditorRole` class (AC-5).
3. **`test_audit.py` — two exact key-set assertions relaxed to
   supersets, plus chain fields.** The L2 assertions that entries
   carry *exactly* `{ts, actor, action, target, details}` now
   require those keys (and `seq` / `prev_hash` / `hash`) as subsets
   (contract keys ⊆ entry keys), in both the in-memory and JSONL
   tests. One test was added asserting `seq` starts at 0, increments,
   genesis `prev_hash == "0"*64`, and `prev_hash` links to the
   previous `hash`. No other audit assertions changed.
4. **`test_service.py` — additive only.** A `DANA` header constant
   and a new `TestAuditorOverHttp` class (5 tests). Existing
   audit-entry assertions already checked keys with `assertIn`, so
   they tolerate the new chain keys unchanged. Its auth-failure
   counts per username stay below the new default lockout threshold,
   so no lockout trips.
5. **`test_main_cli.py` — additive uplift class.** The module
   docstring now includes `dana=auditor`; a new
   `TestCommandLineUplifts` class (2 tests) checks the startup-line
   substring `"(demo users: alice=admin, bob=member, carol=viewer,
   dana=auditor)"` and the AC-7 CLI flags. The original CLI test is
   unchanged.
6. **`test_negative_control.py` — second control added.** The L2
   membership mutant, its gate, and its four tests are unchanged;
   a new audit-tamper control (above) and a docstring paragraph
   naming it were added.

No other Group 2 test file was modified (`test_workspaces.py`,
`test_messaging.py`, `test_files.py`, `test_calendar.py`,
`test_presence.py`, `test_boards.py`, `test_search.py`,
`test_notifications.py` are byte-identical to Group 2).

## Interpretation notes

Inherited from Group 2 and still in force:

- `list_messages(..., limit=N)` returns the **latest** N messages,
  still in chronological order (the contract bounds the list but
  does not say which end; the shipped implementation takes the
  latest).
- Audit `details` defaults are accepted as `None` or `{}`.
- A `parent_id` naming no message, an unknown board/card id, and
  similar not-found-vs-validation edges are accepted as either
  `ValidationError` or `NotFoundError` where the contract names only
  one of the two explicitly for the sibling case.
- Over HTTP, statuses the contract does not pin (add-member,
  card move, mark-read, presence PUT) are accepted as 200 or 201;
  creation endpoints the contract does pin to 201 are asserted as
  201, and auth failures are asserted as exactly 401 per the
  contract ("unknown user or mismatched role → 401").
- List endpoints over HTTP are accepted either as a bare list or
  wrapped (`{"workspaces": [...]}`, `{"messages": [...]}`, …),
  except where the contract pins the wrapper (`/notifications` →
  `{"notifications": [...]}`, `/audit` → `{"entries": [...]}`).

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic.
- `GET /audit/verify`'s `entries` count is read **before** the
  verify's own `audit_read` entry is recorded, so immediately after
  a verify call the log holds `entries + 1` entries (the verify's
  own). `GET /audit` has the same shape: the returned entries are
  the trail as it stood before that read's own `audit_read` entry
  was appended.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform (technique adapted from analytics-l3).
- Lockout state is scoped to one server instance: `test_lockout.py`
  builds a fresh server per test so failure counters never leak
  between tests, and the expiry test uses `lockout_seconds=0.3`
  with a 0.5 s sleep rather than mocking the clock.
