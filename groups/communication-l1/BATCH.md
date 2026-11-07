# Final GAPS batch — Singleton 37, Communication L1 (1 fork)

Unit: the 8 OPEN entries of GAPS.md section "Singleton 37 —
Communication L1 (1 fork)" (inventory idx 381–388), worked under
`gaps-batch/DECISION.md` (ratified 2026-11-07) and
`PLATFORM-LAYER.md`. Extension code: `src/comm/extensions.py`
(`CommExtensions` wrapping `CommStore`); all 7 core modules are
byte-identical to their pre-batch state (SHA-256 verified against
`scratch/prebatch_hashes.txt`; `store.py` still `6ccd412c…`).
Tests: `tests/test_gaps_batch.py`; suite 82 → 115, all passing.

**No entry is re-judged** — all 8 close at their drafted
dispositions (4 `built`, 4 `reference`). Two near-the-line calls
are stated plainly in the adjudication notes below rather than
re-judged: the identity-resolution half of idx 383 and the
records-surface form of idx 387.

Doctrines held: opaque `*_ref` / `*_label` strings and core record
ids only — no record shape on the extension surface can hold a
message subject, body, or any content (pinned by a recursive key
scan); derived-never-stored (campaign lifecycle state, segment
membership, profile contact sets, interaction current outcome,
report figures, operation counts — stored records carry no
derived key, pinned by tests); RBAC through the core `access`
module with denied attempts audited (`:denied`); every extension
mutation audited with an `ext_` prefix; failed operations consume
no ids. The baseline framing is untouched: Low / L1, audit on the
FedRAMP Low side only, no AU-6/AU-9 or Moderate apparatus imported.

## Per-entry disposition

| idx | Entry (GAPS.md text) | Drafted | Final | What was built |
|---|---|---|---|---|
| 381 | Campaign orchestration engine (visual campaign orchestration, cross-channel campaign execution, campaign / journey lifecycle; the fork's signature function) | stub | reference | Campaign definitions held as data (`cmp-`, steps/channel kinds/optional core template binding; `reference_stub: True`, `definition_only: True`, `orchestrated_here: False`, `executed_here: False`); append-only lifecycle state records (`cst-`) with `current_state` derived at read by the latest-record seam (stored definition pinned to carry no state key); send records (`csn-`) binding a campaign to an existing core message (`reference_transport: True`, `transmitted_here: False`) — recording a send dispatches nothing and leaves the bound delivery `queued` with no receipt (pinned). No visual editor, no journey execution. |
| 382 | Audience segmentation engine (targeted segmentation over audience data) | build | built | Segment definitions (`seg-`) whose criteria are held as data (`has_channel_kind` / `in_group` / `name_contains`, validated at definition); membership and count derived at read over the core directory by the seam `_criteria_match` (AND semantics) — the stored definition is pinned to an exact key set with no member/count key; `audience_source: "core_directory"`, `external_audience_here: False`. The batch's fresh negative control targets this seam. |
| 383 | Customer profile store & identity resolution (beyond the directory's contact records) | build | built (store form; resolution not performed — see note 1) | Profile records (`prf-`) keyed by a caller-supplied opaque `profile_ref` (duplicates rejected whole, no id consumed), holding asserted contact ids and opaque attribute labels; link records (`plk-`) for later caller-asserted profile↔contact links (duplicates rejected, mirroring the core's group rule); `profile_view` derives the full contact set at read. Every record carries `resolved_here: False` / `identity_resolution_performed: False` / `merged_here: False`: links are assertions recorded, never inferences made. |
| 384 | Real-time interaction management (real-time decisioning / interaction handling) | build | built (records form) | Interaction session records (`int-`) over a core contact + channel kind, with decision and outcome labels stored verbatim as reported (`live_here: False`, `decisioning_here: False`, `decided_here: False` — the labels are reports about decisions taken elsewhere); append-only follow-up outcome records (`ioc-`); `interaction_view` derives the current outcome at read by the latest-record seam, falling back to the session's own reported outcome, then `unreported`. No session is live and no decisioning runs. |
| 385 | Workflow / BPM engine (campaign-creation workflow as an engine incl. approval chains; claim remainder — the approval-less dispatch substrate is Core) | stub | reference | Workflow definitions held as data (`wfl-`, steps including approval steps whose approver is a role label; `reference_stub: True`, `executed_here: False`, `approvals_enforced_here: False`) + reported outcome records (`woc-`, outcomes verbatim). The registry never executes: defining a workflow and recording outcomes is pinned to change no core message or contact record. Approval steps gate nothing here; the approval-less dispatch substrate remains Core, exactly as the entry's own text records. |
| 386 | Reporting / analytics engines beyond the records substrate (campaign-effectiveness analytics and dashboards) | build | built | `report_summary` — deterministic counts over core + extension records (contacts, groups, messages, deliveries by status, extension record counts), computed at read on every call (`method: deterministic_counts`); `campaign_effectiveness` — per-campaign delivery counts by status derived by walking the campaign's send records to their core deliveries. No report result is ever stored: the figures are pinned to track records created after a first call. No effectiveness score is computed, and no dashboard is rendered. |
| 387 | Real channel execution (email / SMS / push delivery networks and direct-mail fulfillment; core dispatch is the labelled reference transport and transmits nothing) | stub | reference | Execution-channel configuration records (`exc-`, admin-only via the core `channel_write` action, matching the core's channel discipline; kind labels include `postal` for direct mail, which has no core channel kind) + execution records (`exr-`) binding a configuration to an optional core message or an opaque `fulfillment_ref`. Every record carries `reference_stub: True`, `reference_transport: True`, `transmitted_here: False`; recording an execution is pinned to change no core delivery. See note 2. |
| 388 | Managed-service operations (hosting / operating the platform itself) | stub | reference | Operation report records (`sop-`, operation/outcome labels verbatim as reported; `reference_stub: True`, `hosted_here: False`, `operated_here: False`) + `operations_summary` counts derived at read. PLATFORM-LAYER.md decision 6 (hosting is a deployment property) stands beside this closure, as in the Fleet Management L1 unit's adjudicated form for the identical shape; nothing here hosts or operates anything. |

## Adjudication notes

**1. idx 383 — the profile store is built; identity resolution
is not performed, and the record says so.** The entry bundles two
functions. The store half is honestly buildable in this substrate
and is built: profile records keyed by caller-supplied opaque
references, with caller-asserted contact links. The resolution
half — inferring that two contacts or profiles are the same
person — is not a records function, and performing a merge
silently would be the one dishonest move available here. So links
exist only where a caller asserted them, duplicate refs and
duplicate links are rejected rather than merged, and every record
carries `resolved_here: False`. The entry closes `built` in the
store form with the boundary on the records themselves, rather
than `reference`: the deliverable the substrate can honestly
carry (the store) is genuinely built, and the part it cannot
carry is named on every record instead of absorbed silently.

**2. idx 387 — a records surface around a labelled reference
transport, per the entry's own bounding text.** As with the
untiered set's real-channel-transports entry, the entry's text
bounds its own deliverable: "(core dispatch is the labelled
reference transport and transmits nothing)". What is built is the
records surface — configuration records gated exactly as core
channels are, execution records binding real core messages —
with the reference labeling carried on every record and a pin
that recording changes no core delivery. The drafted token is
`reference` and stands: unlike the untiered sibling, this entry
names the delivery networks and the postal fulfillment itself,
not just the transport surface around them, and neither a
network nor a fulfillment exists here in any form.

**3. Campaign sends (idx 381) bind, they do not dispatch.** A
campaign send record states that a core message belongs to a
campaign. The message's deliveries move only when the core's own
dispatch runs them through the labelled reference transport —
the extension never calls dispatch, and the pin in
`test_campaign_send_binds_message_and_dispatches_nothing` holds
the bound delivery at `queued` with no receipt after recording.

## Negative control (fresh, mutation-verified)

Seam: `_criteria_match` in `src/comm/extensions.py` — a segment's
members are exactly the contacts for which every criterion
holds. Mutation (the seam's return line → `return True`, exact
full-line match, one occurrence): suite ran 115 tests, **exactly
5 failures** — the three canonical segmentation tests and both
negative-control canonical legs, all in `tests/test_gaps_batch.py`
and all derivation-dependent; no core test failed. Restored from
`scratch/extensions.py.premutation`, SHA-256 verified identical
(`662f99c3…`), suite re-ran 115, OK. Recorded in
`tests/README.md`.

## Not covered

Nothing outside the 8 entries of this section. The section's
platform-layer paragraph (encryption at rest, TLS-when-configured,
multi-tenancy, demo identities / IA-2) stands on PLATFORM-LAYER.md
and was not absorbed. The founding group's (Group 11) and the
untiered set's gap entries belong to their own batch units and
were not touched. HTTP exposure of the extension surface is out
of scope for the batch pattern (extensions land in `src/` with
tests); the service layer is untouched.

Left unresolved: nothing in this unit.
