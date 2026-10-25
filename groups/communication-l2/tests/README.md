# Tests — Communication L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/communication-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 82 tests
```

Status at delivery: **82 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/operator/viewer, `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording each mutation action, failed ops record nothing |
| `test_contacts.py` | Directory contacts — creation shape/provenance, `ct-` ids, get/list sorted by id, validation (empty name/addresses, bad kind, empty address), viewer write denied, failed ops consume no ids |
| `test_groups.py` | Directory groups — `grp-` creation, add member, duplicate membership → `ValidationError`, unknown ids → `NotFoundError`, `list_group_members` returns contact dicts |
| `test_channels.py` | Channels — all four known kinds {email, sms, voice, push}, `ch-` ids, invalid kind, `channel_write` admin-only, `set_channel_enabled` |
| `test_templates.py` | Templates — `tpl-` creation, `render_template` substitutes every placeholder, missing variable → `ValidationError`, extra variables ignored |
| `test_messages.py` | Message composition + delivery records — literal and template compose, recipient union deduped order-stable, default kind order email,sms,voice,push, `skipped_recipients`, zero-deliveries → `ValidationError` with no message/id consumed, malformed `send_at` |
| `test_dispatch.py` | Dispatch with receipts + scheduling — reference-transport receipt labelled `reference_transport: True`, disabled/absent channel → `failed`/`no_enabled_channel`, `send_at` gate (`dispatch_due` skips future, explicit `now` string/datetime, `dispatch_message` future → `ValidationError`), viewer cannot dispatch, no re-dispatch |
| `test_ack.py` | Acknowledgement tracking — ack requires `delivered` status and `require_ack=True`, `ack_status` totals/pending, viewer denied, unknown ids |
| `test_search.py` | Immutable records + search — literal case-insensitive substring over contacts (name + addresses), messages (subject + body), deliveries (address); literal not regex; shape `{contacts, messages, deliveries}` |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer write + channel_write for operator, full flow (contact → group → channel → template → message → dispatch-due → ack → search → audit), `audit_read` admin-only, denied attempts audited with `:denied`, 400/404 envelopes |
| `test_main_cli.py` | `python -m comm serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `comm_helpers.py` | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a CommStore + AuditLog + a contact + a group containing it + an enabled email channel (created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `CommStore` subclass (`MutantCommStore`) whose
`_first_enabled_channel` always returns a fake enabled channel — the
enabled-channel check is skipped. The traced claim, named in the
module's docstrings, is that **dispatch honors the send gate**: a
disabled or absent channel must fail the delivery with
`failure_reason='no_enabled_channel'`, and a viewer must not dispatch.
For each canonical case (disabled channel, absent channel, viewer
dispatch) the test asserts three things: the canonical expectation
(failed delivery / `PermissionDenied` from the real implementation,
with the delivery staying queued for the viewer case), that the
mutant would NOT produce that expectation (it delivers anyway / waves
the viewer through its gate), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails.

## Mutation verification

VERIFIED by the coordinator (2026-10-25). The send-gate condition in
`CommStore._dispatch_deliveries` (`src/comm/store.py`) — the line
`if channel is None:` immediately following
`channel = self._first_enabled_channel(delivery["channel_kind"])` in
the dispatch loop — was patched to `if False:`, the exact live
counterpart of the mutant in `test_negative_control.py`, so dispatch
delivered even with a disabled or absent channel. The full suite was
run: **82 tests ran, 4 failed** —

- `test_dispatch.TestDispatch.test_dispatch_due_absent_channel_fails`
- `test_dispatch.TestDispatch.test_dispatch_due_no_enabled_channel_fails`
- `test_negative_control.TestNegativeControlMutantDispatch.test_absent_channel_fails_canonical_but_mutant_delivers`
- `test_negative_control.TestNegativeControlMutantDispatch.test_disabled_channel_fails_canonical_but_mutant_delivers`

`store.py` was then restored from a pre-mutation copy (SHA-256
`6ccd412c2c1a836694d74687804aa90abe31f4c54eba62e916c31cb6dc5e6110`,
verified identical to the pre-mutation hash) and the suite re-run:
**82 tests, OK**. The suite catches this defect class; the negative
control is not decorative.
