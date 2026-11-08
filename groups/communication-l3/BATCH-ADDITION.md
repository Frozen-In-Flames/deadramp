# Final GAPS batch — second unit: Remainder Addition — Communication L3-adjacent

Unit: the 2 OPEN entries of the GAPS.md section
**`## Remainder Addition — Communication L3-adjacent (+1 fork)`**
(the +1 fork is GovSlack, Slack Technologies, FR2230252267,
FedRAMP High / Certified, added to this group by the remainder
census; its spec sheet's ADDENDUM §5 registered these gaps).
Built 2026-11-07 under `gaps-batch/DECISION.md` (the 2026-11-07
ratified triage) and `PLATFORM-LAYER.md`.

**Entry-count verification (no discrepancy):** GAPS.md's section
lists exactly 2 `- [ ] open` entries, and
`gaps-batch/inventory.json` assigns exactly idx 658–659 to this
section (658 stub-engine, 659 build-extension). Both sources
agree with the brief's count of 2.

All extension code is one new module,
`src/comm/extensions_addition.py` (`CommExtensionsAddition`, a
second wrapper around the untouched core store, audit actions
prefixed `exta_`); every existing module — the 7 core modules
and the first batch unit's `extensions.py` (`6844a905…`) — is
byte-identical (SHA-256 verified against the pre-build record in
`scratch/prebatch-addition-src.sha256`; `store.py` still
`bfc7877c…`, `audit.py` still `2c719311…`). No core extension
was needed. Tests: `tests/test_gaps_batch_addition.py` (21
tests; suite **186 → 207**, all passing).

Category doctrines held: communication records hold opaque
references and metadata only — no record shape on the addition
surface can hold message content (signatures accept no
content-shaped parameter; `content=` / `body=` / `payload=` /
`document=` calls raise `TypeError`, pinned by calls, a
signature scan, and a recursive key scan over every record and
view); sending/transmission never happens (`sent_here` /
`transmitted_here`: False wherever a sending path could be
inferred); derived values are derived at read and never stored
(connector current outcome and reported-records total, room
member count/list and current activity — stored records carry
no derived key, pinned). The High apparatus binds the addition:
fail-closed audit-before-commit on the core hash-chained log,
and the separated `auditor` role is denied every addition
operation including reads while its core audit duty
(`verify_chain()` → `(True, None)`) works unchanged, pinned.

## Per-entry disposition

| idx | Entry (verbatim GAPS.md text) | Drafted | Final | What was built |
|---|---|---|---|---|
| 658 | App integration & connector platform: connecting third-party software tools and services into the messaging surface (the group's taxonomy has no integrations family at all; the function is asserted in substance only) | stub-engine | **reference** | Connector definition records (`acn-`, kinds: app_integration / api_connector / webhook_connector / data_sync; opaque `connector_ref` unique per surface, verbatim label; `reference_stub: True`, `reference_transport: True`, `connected_here` / `synced_here` / `credentials_held` / `sent_here` / `transmitted_here: False`) + reported exchange records (`aex-`, verbatim outcome labels, optional non-negative integer `records_reported` with bools/floats/negatives refused and no id consumed). `connector_view` derives `current_outcome` (addition seam), `total_records_reported` (a sum of the operator's reported counts, stated as such), and `exchanges_without_count` at read. No third-party tool is connected, no API is called, no credential or payload is held — the connector engine's honest records form, in this category's adjudicated connector form (the brief's integration-shaped closure). |
| 659 | Persistent channel / workspace collaboration surface: channels as persistent team rooms (distinct from the build's delivery-channel records; the workspace substrate proper belongs to the Collaboration groups' builds) | build-extension | **built** (records form) | Persistent room records (`wsr-`, opaque `room_ref` unique per surface, verbatim label; namespace distinct from core delivery channels `ch-`, pinned) + membership records (`wmb-`, binding a core contact validated and read through the core store; duplicate membership refused, no id consumed) + activity records (`wra-`, verbatim activity labels, optional binding to a core message **by id only** — the message is validated through the core store, its content is never copied, and recording activity is pinned to leave the bound delivery `queued`, dispatching nothing). `workspace_room_view` derives member list/count and `current_activity` (addition seam) at read; the stored room carries no derived key. Bounded on every record: `content_held: False`, `real_time_transport_here: False`, `workspace_substrate_here: False` — what is built is the room registry / membership / activity records surface; the workspace substrate proper named in the entry's own parenthetical (the Collaboration groups' builds) is not built here and is not claimed. |

## Re-judgments (DECISION.md qualification 1)

None. Both entries close at their drafted dispositions. idx 659
is the unit's nearest-the-line call and its boundary is stated
plainly: the drafted build stands because a persistent room, its
membership, and its activity are genuinely records-shaped in
this substrate (rooms presuppose exactly the directory and
message records the core already holds), while the entry's own
text assigns the workspace substrate proper to the Collaboration
groups — that half is stated absent on every record
(`workspace_substrate_here: False`) rather than built or
implied. If the parent prefers the bundle tokened `reference`
for that stated absence, the build is identical; the records
surface is the full honest deliverable either way.

## Negative control (fresh, mutation-verified)

Seam: `_latest_label` in `src/comm/extensions_addition.py` —
the current reported label of an append-only record stream is
its LATEST record's label (used by the connector view's current
outcome and the room view's current activity). Live drill on
the real file: the seam's return line (`return records[-1][key]`,
line 87, the module's only occurrence, count asserted = 1
before patching) was patched to `return records[0][key]`; the
full suite ran 207 tests with **exactly 5 failures**, all in
`tests/test_gaps_batch_addition.py` —

- `test_gaps_batch_addition.TestConnectorReference.test_exchange_and_view_derived`
- `test_gaps_batch_addition.TestWorkspaceRoomBuilt.test_current_activity_derived_from_latest`
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_canonical_view_uses_latest_activity`
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_mutant_earliest_differs` (trips by design: it asserts the literal canonical value against the real implementation)
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_canonical_expectation_rejects_mutant`

No core or first-unit test failed. Restored from
`scratch/extensions_addition.py.premutation`, SHA-256 verified
identical (`087125da…`), suite re-ran **207, OK**. Recorded in
`tests/README.md`; raw output in
`scratch/gaps_addition_mutation_run.txt`.

## Not covered

Nothing outside the 2 entries of this section. The section's
closing paragraph in GAPS.md (the search & eDiscovery
by-substance enlargement, the explicitly-no-claimant notes for
secure transmission and workflow, and the standing video
conferencing named absence at 0 of 7 forks) names no open entry
and was not absorbed. HTTP exposure of the addition surface is
out of scope for the batch pattern; the service layer is
untouched. PLATFORM-LAYER.md decisions 1–6 are untouched: no
identity provider, no validated cryptography, no retention
enforcement, no session layer, and no hosting or multi-tenancy
claim was built or implied.

Left unresolved: nothing in this unit.
