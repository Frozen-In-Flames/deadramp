# Final GAPS batch — Untiered Set 13, Communication (2 forks, tier null)

Unit: the 9 open entries in GAPS.md under "Untiered Set 13 —
Communication (2 forks, tier null)" (idx 865–873 in
`../../gaps-batch/inventory.json`; 5 `build-extension`,
4 `stub-engine`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
is re-judged.** One near-the-line call — the real-channel-transports
entry — is stated plainly in adjudication note 1 below rather than
re-judged. The section's tenth entry (idx 874, platform layer)
was already closed `re-scoped` under `../../PLATFORM-LAYER.md`
and is not part of this unit.

All extension code is in one new module,
`src/comm/extensions.py` (`CommExtensions`, wrapping the core
`CommStore`); every existing core module is byte-identical to
its pre-batch state (SHA-256 verified against the accounting in
this group's README; `store.py` still `6ccd412c…`). Full suite:
100 tests before, **140 tests after, OK** (40 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline binds the extension surface exactly as it
binds the core.** Nothing here asserts or records a tier, a
control baseline, or an equivalence: no record shape carries a
tier-shaped key, and a test scans every extension record and
derived view recursively for tier/baseline/equivalence keys (and
for floats and numeric lists). The forks' documented control
claims remain where `UNION-SPEC.md` put them — the forks' claims
about themselves, recorded in the spec; the surfaces below build
the records forms of functions the forks *describe*, and claim
no control attainment for them.

Cross-cutting, per the group's doctrines: RBAC is enforced
through the core `comm.access` matrix — the extension maps each
operation onto an existing core action (the core action set is
fixed: record writes to `message_compose`, transport channel
configuration to `channel_write`, reads to `records_read`) and
checks it before any state change or id allocation; denied
attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`; all parties, networks, and content are opaque
`*_ref` / `*_label` strings or core record ids, and no record
shape can hold message content, shared content, audio, or media;
derived values (current presence, current accountability status
and location, muster counts, federation exchange counts) are
computed at read by the seam `_latest_report` and never stored;
the crisis-orchestration registry never executes — defining a
campaign and recording dispatch requests changes no core message
or delivery record (pinned by before/after equality test).

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `comm/extensions.py`) |
|---|---|---|
| Presence & availability services | built | `record_presence` (`prs-`, one reported label per record over a core contact; state enum available / busy / away / do_not_disturb / offline), `presence_view` — current state derived at read by the seam `_latest_report` (latest recorded report wins; `unreported` when none), the stored record pinned to an exact key set with no derived key; the batch's fresh negative control targets this seam |
| Desktop sharing & collaboration content sharing | built | `record_content_share` (`shr-`, sharer = core contact, optional core-contact recipients, content held only as an opaque `content_ref`; `content_held_here: False`, `rendered_here: False`) — no parameter can accept content or media (pinned by TypeError tests) |
| Personnel accountability, location/status visibility & field-reporting platform | built | `record_status_report` (`acc-`, status enum safe / injured / missing / unaccounted / evacuated; `location_label` held verbatim as caller-reported data, `location_source: "caller_reported"`, `tracked_here: False` — nothing is sensed or tracked), `accountability_view` (current status/location derived at read by the seam), `muster_summary` — reported/unreported totals and per-current-status counts derived at read over all contacts or one core group's members; counts only, no score |
| Inter-organizational federated communication networks | built | `record_federation_link` (`fed-`, opaque `network_ref` + peer label; `reference_transport: True`, `live_network_here: False`), `record_federation_exchange` (`fxg-`, binds a link and an optional core message; outcome stored verbatim as reported; `reference_transport: True`, `transmitted_here: False`), `federation_link_view` — exchange count derived at read; the stored link record carries no count (pinned by test) |
| Real channel transports (the build's transport is a labelled reference stub, never a real channel) | built (records surface; see note 1) | `configure_transport_channel` (`trc-`, admin-only via the core `channel_write` action, matching the core's channel discipline; `reference_transport: True`, `real_channel_here: False`, `transmitted_here: False`), `record_channel_dispatch` (`trd-`, binds a configuration record to a core message; `reference_transport: True`, `transmitted_here: False`, status `recorded_reference_only`) — recording a dispatch changes no core delivery (pinned: the bound message's delivery stays `queued` with no receipt until the core's own dispatch runs it through the reference transport) |
| Video conferencing, meetings & real-time media transport engines (no taxonomy family exists for them in this category; the standing absence continues) | reference (stub-engine) | `record_meeting_session` (`mtg-`, title label, optional organizer/participant core contacts, optional scheduled time; `reference_stub: True`, `media_here: False`, `connected_here: False`) — `reference_stub: True` throughout; no parameter can accept media (pinned by TypeError tests); the taxonomy absence itself is untouched — this closes the gap entry as a labeled reference implementation, it does not create a family or a claim |
| Voice/telephony media, call-control & endpoint interoperability engines | reference (stub-engine) | `record_call` (`cal-`, caller/callee core contacts, outcome label stored verbatim as reported; `reference_stub: True`, `connected_here: False`, `media_here: False`) — no call is placed or connected |
| Crisis-communication orchestration & multi-channel alerting engines | reference (stub-engine) | `define_alert_campaign` (`cmp-`, definition held as data: name, channel kinds, optional core template binding; `definition_only: True`, `reference_stub: True`, `orchestrated_here: False`, `executed_here: False`), `record_campaign_dispatch_request` (`cdr-`, `reference_stub: True`, `reference_transport: True`, `dispatched_here: False`) — the registry never executes (pinned: core messages/deliveries byte-identical before and after) |
| Voicemail & unified messaging engines | reference (stub-engine) | `record_voicemail` (`vm-`, recipient core contact, caller label, opaque `media_ref`; `reference_stub: True`, `recorded_here: False`, `media_held_here: False`) — no parameter can accept audio (pinned by TypeError tests); no audio content field exists |

## Adjudication notes

**1. Real channel transports — built as a records surface, the
transport itself the labeled reference, per the entry's own
bounding text.** The entry's text bounds its own deliverable:
"(the build's transport is a labelled reference stub, never a
real channel)". What the entry asks for is therefore the records
surface around transports — channel configuration records and
dispatch records — with the reference labeling carried on every
record, and that surface is genuinely built in-substrate above:
configurations are admin-gated exactly as core channels are, and
a dispatch record binds a real core message while changing
nothing in the core (the delivery still moves only when the
core's own dispatch runs it through the reference transport).
No real channel is claimed, configured, or implied:
`real_channel_here` and `transmitted_here` are False on every
record the surface creates. This is the founding group's
adjudicated form for transports (dispatch through a deterministic
reference transport, receipts labeled `reference_transport:
true`), restated at the extension layer. The entry is therefore
**not** re-judged; if the parent prefers the `reference` token
for it, only the token changes — the records, labels, and tests
are unaffected.

**2. Presence and accountability derivations share one seam.**
Both entries' current-state values derive from append-only
report records by `_latest_report` (the latest *recorded* report
wins; a caller-supplied `reported_utc` is held as data and does
not reorder the log). One seam means one negative control covers
both entries' derivation claim, and the live drill's failure set
(both entries' canonical tests plus the muster counts that
consume the accountability derivation) is recorded in
`tests/README.md`.

**3. The video family's absence is recorded, not repaired.**
The union spec names video conferencing as this category's
standing absence — no taxonomy family exists for it. The batch
unit closes the registered gap entry with a labeled reference
implementation (session records) and nothing more: no family is
created, no claim is tagged, and the spec's claim table is
untouched.

## Long-tail enumeration

Against the 9 items of this set's gap list in `UNION-SPEC.md`
(each maps to the entry of the same name in the table above):

**Named as NOT covered by this unit** (so nothing is read as
silently absorbed):

- **The section's platform-layer paragraph** (idx 874:
  encryption at rest, TLS-when-configured, multi-tenancy, demo
  identities / IA-2) — already closed `re-scoped` on
  `../../PLATFORM-LAYER.md` before this unit; no entry here
  absorbs or re-opens it.
- **The founding group's remaining extended gaps**, registered
  under Group 11 (Communication L2) and not re-registered here,
  per the union spec: email-security and AI/ML engines,
  archiving / eDiscovery engines, casework depth, key/certificate
  automation, end-to-end encrypted transport, tracking platform
  depth, permits / payments / e-signature engines, workflow/BPM
  and reporting/analytics engines. Those entries belong to the
  founding group's own batch unit; nothing here re-closes them.
- **The paired record F1302271924A** (AtHoc "- High",
  Collaboration L3-adjacent) is a separate registry offering
  with its own group and its own gap registrations; nothing in
  this unit touches it.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
