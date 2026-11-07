# Tests — Collaboration L1 (Group 10) merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Reuse

This build is an explicit, in-full reuse of our own shipped Group 2
(Collaboration L2) code — Operation DeadRamp, Apache-2.0, ours. The
implementation is functionally tier-neutral (a grep of Group 2's
`src/` tree finds no tier/baseline strings), so the same code ships
here unchanged. The **code** is reused in full; the **baseline claims
are NOT inherited** — Group 2's Moderate-baseline claims do not carry
over. This group's claims are the **Low baseline / FAR 52.204-21**
only, per its `UNION-SPEC.md`. See `../scratch/reuse-note.md` for the
per-file SHA-256 comparison.

## Run

```bash
cd groups/collaboration-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 192 tests
```

Status at delivery: **192 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers (UNION-SPEC Core) |
|---|---|
| `test_access.py` | 10 Access control — exact permission matrix for admin/member/viewer, `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | 11 Audit log — entry keys, append-only, JSONL file + reload on construction, and the store recording each mutation action (`workspace_create` … `notification_read`, `search`) |
| `test_workspaces.py` | 1 Workspaces — creation shape/provenance, `ws-` id sequence, list visibility, owner-or-admin `add_member`, duplicate add → `ValidationError`, non-member get → `PermissionDenied`, failed ops consume no ids |
| `test_messaging.py` | 2 Messaging & chat — channels, post shape, same-channel threading (cross-channel parent → `ValidationError`), chronological list + limit, mentions notifying members only, never the author |
| `test_files.py` | 3 File sharing — versioned records, `sha256` = hashlib of the UTF-8 content, `size_bytes`, re-share → next version, `get_file` returns content, other members notified |
| `test_calendar.py` | 4 Calendaring — event shape, `end <= start` → `ValidationError`, malformed datetimes → `ValidationError`, member attendees notified, non-member attendees not |
| `test_presence.py` | 5 Presence — each of available/busy/dnd/offline, invalid status → `ValidationError`, self-or-admin enforcement, unset → `NotFoundError` |
| `test_boards.py` | 6 Whiteboards — boards, positioned cards, non-numeric x/y → `ValidationError`, move card, per-board scoping |
| `test_search.py` | 7 Search — literal case-insensitive substring over messages/files/events/cards, and the scoping guarantee: results never leak another workspace's objects |
| `test_notifications.py` | 8 Notifications — per-user queue oldest-first, feed kinds (mention/file_share/event_invite), `mark_read` by owner or admin only |
| `test_service.py` | 9 API access — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer posting, full flow (workspace → channel → message → file → event → search → notifications → audit), `audit_read` admin-only over HTTP, denied attempts audited with `:denied` |
| `test_main_cli.py` | `python -m collab serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `collab_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `make_store()` building a CollabStore + AuditLog + a workspace owned by MEMBER with VIEWER added, and sample message/file/event/board helpers |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a membership check that treats **every** actor as a workspace member.
The traced claim, named in the module's docstrings, is that workspace
membership is the AC-3 access-enforcement boundary. For each canonical
case (non-member `post_message`, non-member `share_file`, non-member
`list_messages`, non-member `search`) the test asserts three things:
the canonical expectation (`PermissionDenied` from the real
implementation, with nothing stored), that the mutant gate would NOT
raise (it waves the non-member through), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome as
the expected outcome fails.

## Mutation verification

VERIFIED for this Group 10 tree (2026-10-25). The membership condition
in `CollabStore._require_workspace_access` (`src/collab/store.py`) —
the condition that raises `PermissionDenied` for non-members — was
patched to `if False:` — the exact live counterpart of the mutant in
`test_negative_control.py`, waving every non-member through — and the
full suite was run: **192 tests ran, 14 failed**. The failures span
every membership-gated surface, across 8 test files: the 4
negative-control tests, plus non-member cases in `test_workspaces`
(2), `test_messaging` (2), `test_boards` (2), `test_files` (1),
`test_calendar` (1), `test_search` (1), and `test_service` (1, the
HTTP 403 case). Full mutant-run output is kept at
`../scratch/mutation-run.txt`. `store.py` was then restored from the
pre-mutation copy at `../scratch/store.py.pristine` (SHA-256
`d2b943e29a592c3f9b007e2cc6ca399e90b6127a446b9380e927f1c3b01f577a`,
verified identical to the pre-mutation hash, `diff` empty) and the
suite re-run: **192 tests, OK**. The suite catches this defect class;
the negative control is not decorative.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite follows the
shipped implementation's documented choices and stays tolerant of the
remaining freedom:

- `list_messages(..., limit=N)` returns the **latest** N messages,
  still in chronological order (the contract bounds the list but does
  not say which end; the shipped implementation takes the latest).
- Audit `details` defaults are accepted as `None` or `{}`.
- A `parent_id` naming no message, an unknown board/card id, and
  similar not-found-vs-validation edges are accepted as either
  `ValidationError` or `NotFoundError` where the contract names only
  one of the two explicitly for the sibling case.
- Over HTTP, statuses the contract does not pin (add-member,
  card move, mark-read, presence PUT) are accepted as 200 or 201;
  creation endpoints the contract does pin to 201 are asserted as 201,
  and auth failures are asserted as exactly 401 per the contract
  ("unknown user or mismatched role → 401").
- List endpoints over HTTP are accepted either as a bare list or
  wrapped (`{"workspaces": [...]}`, `{"messages": [...]}`, …), except
  where the contract pins the wrapper (`/notifications` →
  `{"notifications": [...]}`, `/audit` → `{"entries": [...]}`).

## Final GAPS batch — `test_gaps_batch.py` (38 tests)

Covers the extension surface in `../src/collab/extensions.py`
(`CollabExtensions`; see `../BATCH.md` for the per-entry
dispositions, idx 104–112): learning records (course shape,
enrollment membership boundary, verbatim completions with
`assessed_here: False`, derived course counts, viewer read /
non-member denial audited as `ext_course_create:denied`); knowledge
management (stored article record pinned to exactly
`{id, workspace_id, tags, created_by, created_utc}` — no text on
the stored record; current text derived from the latest revision;
search over current text only); task/project depth (milestones
over core boards, card links, verbatim card states, state counts
derived at read with no score/percent/progress key, state records
leaving core cards untouched); records & governance (policy
validation and the admin-only `manage_members` mapping, hold
currency derived at read, holds leaving core files byte-identical,
eligibility derivation incl. the `at` override, gated disposition
decisions with `executed_here: False`); the five reference
families' labels and behavioral pins (assistant reports leaving
core messages untouched, transcription report shape holding no
transcript field, analytics as deterministic counts that move as
records are added, workflow definitions leaving core records
byte-identical, voice/meeting records with `media_here: False`,
envelope shape pinned to a key set that can hold no signature
value, ceremony signer membership); and the audit-rollback pin
(a failing audit write rolls back the record and its id).

### Batch negative control — disposition eligibility

`TestDispositionEligibilityNegativeControl` implements the batch's
fresh mutant for the new code: `_disposition_eligible` in
`src/collab/extensions.py` replaced by an always-eligible gate.
The traced claim is that a disposition decision may be recorded
only when the file's recorded retention period has run **and** no
hold is active over it. For each canonical case (file under an
active hold with retention met; file within its retention period
with no hold) the test asserts the canonical expectation (the real
gate refuses with `ValidationError` and stores nothing), that the
mutant gate would NOT refuse (it records the decision / reports
eligible), and — via a literal `assertRaises(AssertionError)` —
that treating the mutant's outcome as the expected outcome fails.
The mutant shares the canonical instance's tables, so only the
seam differs.

**Mutation verification (live drill, 2026-11-07):** the seam body
in the real `src/collab/extensions.py` was patched to
`return True` and the full suite was run: **230 tests ran, exactly
3 failed**, all in `test_gaps_batch.py`:
`TestDispositionEligibilityNegativeControl.test_held_file_refused_canonically_but_mutant_allows`,
`TestDispositionEligibilityNegativeControl.test_within_retention_refused_canonically_but_mutant_allows`,
and `TestGovernance.test_eligibility_derivation`. No core test
failed — the mutant changes only disposition eligibility, which is
the point. Full mutant-run output is kept at
`../scratch/gaps_batch_mutation_run.txt`. `extensions.py` was then
restored from `../scratch/extensions.py.premutation` and verified
byte-identical by SHA-256 (`980a3ab5…`, in
`../scratch/extensions.py.sha256`), and the suite re-run:
**230 tests, OK**.
