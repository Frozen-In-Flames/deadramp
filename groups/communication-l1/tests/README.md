# Tests — Communication L1 singleton build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to. The suite is the shipped
Group 11 (Communication L2) suite inherited for this singleton: 13 of
15 files byte-identical, 2 differing by docstring wording only
(group references; zero logic changes — see
`../scratch/reuse-note.md`).

## Run

```bash
cd groups/communication-l1
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

VERIFIED in this tree (2026-10-25). The send-gate condition in
`CommStore._dispatch_deliveries` (`src/comm/store.py`) — the line
`if channel is None:` immediately following
`channel = self._first_enabled_channel(delivery["channel_kind"])` in
the dispatch loop — was patched to `if False:`, the exact live
counterpart of the mutant in `test_negative_control.py`, so dispatch
delivered even with a disabled or absent channel. The full suite was
run: **82 tests ran, 4 failed** (full output in
`scratch/mutation-run.txt`) —

- `test_dispatch.TestDispatch.test_dispatch_due_absent_channel_fails`
- `test_dispatch.TestDispatch.test_dispatch_due_no_enabled_channel_fails`
- `test_negative_control.TestNegativeControlMutantDispatch.test_absent_channel_fails_canonical_but_mutant_delivers`
- `test_negative_control.TestNegativeControlMutantDispatch.test_disabled_channel_fails_canonical_but_mutant_delivers`

`store.py` was then restored from the pre-mutation copy in
`scratch/` (SHA-256
`6ccd412c2c1a836694d74687804aa90abe31f4c54eba62e916c31cb6dc5e6110`,
verified identical to the pre-mutation hash recorded in
`scratch/store.py.sha256`) and the suite re-run: **82 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.

## Final GAPS batch tests (appended at the batch build)

| Module | What it pins |
|---|---|
| `test_gaps_batch.py` | The 8 open entries of this singleton's gap list (inventory idx 381–388) closed in records/reference form: campaign definitions as data with lifecycle state derived at read and send records pinned to dispatch nothing; segment membership derived at read over the core directory (stored definition pinned to an exact key set with no derived key); profile records keyed by caller-supplied opaque refs with caller-asserted links (`resolved_here: False`); interaction session records with verbatim reported labels and current outcome derived at read; workflow definitions as data, pinned to change no core record; report figures as deterministic counts derived at read (proven to track records created after a first call); execution-channel records pinned to change no core delivery; managed-service operation records with counts derived at read. Cross-cutting: reference-stub labels on the four stub families, no content-shaped key (subject/body/content/audio/media) anywhere on the extension surface, failed operations consuming no extension ids, denied writes audited `:denied`, mutations audited with the `ext_` prefix, and the batch's fresh negative control below. |

### The segmentation seam drill (fresh negative control, batch)

The claim under test: **a segment's members are exactly the core
contacts for which every recorded criterion holds** — the
membership is derived at read from the segment definition's
criteria by `CommExtensions._criteria_match` (AND semantics), the
single evaluation point behind `segment_view`.
`TestNegativeControlSegmentMembership` pins two canonical cases
(a channel-kind criterion; two ANDed criteria) and, for each,
asserts (1) the real implementation's outcome, (2) a mutant
subclass overriding the seam to wave every contact through would
NOT produce it (it returns the whole directory), and (3) treating
the mutant's outcome as the expected outcome raises
`AssertionError`.

File-level verification (performed at build time, raw output in
`scratch/gaps_batch_mutation_run.txt`): the shipped
`src/comm/extensions.py` (pre-mutation SHA-256
`662f99c3bdd2bb1d075783c05ac47ab622d79c4c3de854b330d1b7fb0fce4b2a`,
backup in `scratch/extensions.py.premutation`) was mutated at the
seam's return line (`return all(_criterion_holds(...) ...)` →
`return True`, exact full-line match, one occurrence) and the
full suite run: **exactly 5 failures** out of 115 —

- `test_gaps_batch.TestAudienceSegmentation.test_segment_by_channel_kind`
- `test_gaps_batch.TestAudienceSegmentation.test_segment_by_group_and_name`
- `test_gaps_batch.TestAudienceSegmentation.test_segment_criteria_are_anded`
- `test_gaps_batch.TestNegativeControlSegmentMembership.test_channel_kind_criterion_canonical_but_mutant_waves_all`
- `test_gaps_batch.TestNegativeControlSegmentMembership.test_anded_criteria_canonical_but_mutant_waves_all`

— all in the batch's own new tests and all
segmentation-derivation-dependent; no core test failed. The file
was then restored from the pre-mutation copy, its SHA-256
verified identical, and the suite re-run green. Run count after
the batch: **115 tests, OK** (82 before; 33 added by the batch
module).
