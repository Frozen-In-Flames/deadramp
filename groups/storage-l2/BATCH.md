# Final GAPS batch — Remainder Singleton 64, Storage L2

Date: 2026-11-07. This singleton's section of `../../GAPS.md`
listed 10 open entries (inventory idx 725–734); all 10 are
closed by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/storage/extensions.py`
(`StorageExtensions`, wrapping the core `StorageStore`; all
seven core modules byte-identical, SHA-256 verified against the
pre-build baseline — store.py still `37314f3d…`), and
`tests/test_gaps_batch.py` (43 tests). Full suite: **79 → 122
tests**, all passing.

The founding disciplines bind every shape built here. The core
holds metadata records only — no field can hold a subject, a
body, or any content — and neither can any extension shape:
pinned by exact key-set assertions per record type, by a
recursive forbidden-key scan over every extension record and
view, and by `TypeError` on any unexpected keyword argument (a
`content=`, `key_material=`, or `query_text=` argument can
never enter a shape). Nothing here captures, encrypts, delivers,
executes, connects, or destroys: PLATFORM-LAYER.md decision 2
(no build claims FIPS-validated cryptography; a fork's posture
is recorded as the fork's), decision 3 (builds perform no
cryptography of their own), and decision 4 (retention and
disposition enforcement is the embedding organization's records
schedule, executed at the deployment layer) are load-bearing for
this unit and are cited per entry below.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 725 | Archived payload storage plane: storing the actual archived content (the Core holds metadata records only — no field can hold a subject, body, or content) | built | Payload custody records (`pay-`; action: custody): a custodian opaque reference, the payload byte count **as reported** by that custodian, and an opaque checksum reference, bound to a core message record — one per message. `content_held_here: False` on the shape, and the shape provably has no field that could hold the payload. `payload_custody_view` derives `size_matches_record` at read (reported count vs the core record's recorded size) through no stored key. What lands is the custody accounting of the plane; see the near-the-line statement below. |
| 726 | Archive ingest pipeline: capturing messages into the archive | built | Ingest-batch records (`ing-`; action: archive) against a registered mail-platform integration (a directory integration is refused): source label plus message/byte counts stored **as reported** by the external capture system, `captured_here: False`. Recording a batch archives nothing — pinned by test that core message records and the core summary are byte-identical before and after. |
| 727 | Full-text content indexing & search engine (discovery records in the Core carry no free-text query field by design) | reference | Index reference records (`idx-`; action: discover) carrying `reference_stub: True`, `index_built_here: False`: an engine label and its document count as reported. **No search or query surface of any kind exists on the extension** — pinned by test (no attribute name contains "search" or "query"; a `query_text=` keyword raises `TypeError`). The substrate holds no content to index, so the honest landing form is the reference record. |
| 728 | Encryption & decryption engine (the encryption family is Extended; the build performs no cryptography — its custody records are Core) | built | Encryption profile records (`enc-`; action: custody) extending a core key-custody record — one per custody record: the algorithm named by an opaque label, and the fork's own stated validation posture recorded verbatim **as the fork's** (`validation_transfers: False`, PLATFORM-LAYER.md decision 2). `encrypted_here: False`; per decision 3 no cryptographic operation exists anywhere in the module — pinned by a test scanning the module's import lines (no crypto library is imported, and no other stdlib path to one is used). |
| 729 | Key management hardware & premise equipment | reference | Key-hardware inventory records (`khw-`; action: custody) carrying `reference_stub: True`, `key_material_held_here: False`: an equipment label and a location label bound to a core custody record. The equipment is the custodian's, in the customer environment; this is its inventory landing form. No key material exists in any shape, here as in the core. |
| 730 | Retrieval delivery transport & export file production | built | Delivery records (`dlv-`; action: retrieve), one per core retrieval, carrying `reference_transport: True`, `delivered_here: False`: the transport named by label; `delivery_view` derives the linked retrieval's current status at read (stored record carries no status key). Export manifest records (`exp-`): a format label and the collection's own message ids the export would contain, each resolved against the core records (a foreign collection's message is refused whole); `files_produced_here: False`, and `file_count` is derived in the view, never stored. Files are described, never produced; messages are never placed anywhere. |
| 731 | Supervision review console & workflow engine | reference | Console definition records (`wfd-`; action: supervise) holding a label and reviewer references **as data**, `reference_stub: True`, `executed_here: False` — definitions are held, never executed (the house registry rule). Console assignment records (`wfa-`) bind a core review to a definition and the reviewer reference the definition names (an unnamed reviewer is refused), `routed_here: False`; recording one changes no core review record (pinned). Reviewer decisions themselves stay in the core review records, recorded verbatim there — the console surface adds no second decision store. |
| 732 | Policy enforcement execution (enforcement records are Core; nothing executes) | built | Enforcement decision records (`dec-`; action: enforce): an action from the core's own enforcement vocabulary (`ENFORCEMENT_ACTIONS`, imported from the core so the vocabularies cannot drift) under a stated policy reference, `executed_here: False`. Recording is **gated by the fresh negative control's seam** (below): the message's derived retention state at the decision moment comes from the core's seam, and a decision for a `disposed` message is refused whole. Recording a decision changes no core record (pinned: message view and core enforcement list byte-identical before/after). `enforcement_decision_view` derives the current state and current actionability at read. |
| 733 | Mail platform & directory connectors | reference | Connector sync receipt records (`syn-`; action: register) carrying `reference_stub: True` and `reference_transport: True`, `connected_here: False`: a direction label and a synced count stored as reported, bound to a registered core integration. Recording a receipt opens no connection, authenticates no one (identity stays with the embedding organization, PLATFORM-LAYER.md decision 1), moves no message, and changes no core record (pinned). |
| 734 | Disposition execution: destroying the payload itself (the Core's disposition is a derivation-gated record) | built | Disposition outcome records (`dout-`; action: archive) bound to a core disposition record: the outcome label stored **as reported** from the `reported_*` vocabulary (`reported_destroyed` / `reported_failed` / `reported_pending`), `destroyed_here: False`. The current outcome is derived at read through `_current_outcome_label` (latest recorded label, else `unreported`) and stored nowhere; recording outcomes leaves the core disposition record byte-identical (pinned). Per PLATFORM-LAYER.md decision 4, destroying the payload is the deployment layer's act under the embedding organization's records schedule; its reported outcome lands here. This build holds no payloads to destroy. |

Closure tokens: 6 entries close as `built` (725, 726, 728, 730,
732, 734) and 4 as `reference` (727, 729, 731, 733) — exactly
the drafted triage split; no entry was re-judged.

## Fresh negative control

The batch's fresh mutation-verified negative control is the
enforcement-eligibility seam,
`StorageExtensions._derive_enforcement_eligibility` in
`src/storage/extensions.py`: a decision for a message whose
derived retention state is `disposed` must be refused whole
(nothing stored, no id consumed), because once disposition is
recorded there is nothing left in this substrate for a decision
to concern. Verified two ways (full record in
`tests/README.md`):

1. **In-suite mutant** (`TestEnforcementEligibilityNegativeControl`):
   the canonical refusal is asserted on the real implementation;
   a mutant subclass whose seam reports every state eligible
   waves the same decision through; treating the mutant's
   outcome as the expectation fails.
2. **External drill**: the seam's comparison in the real file
   was patched to `return True`, the full suite re-run —
   **exactly 2 failures out of 122**, both in the batch's own
   new tests (`TestEnforcementDecisions.test_view_derives_current_state`,
   `TestEnforcementEligibilityNegativeControl.test_decision_for_disposed_message_refused`);
   all 79 pre-existing core tests still passed. The file was
   restored from `scratch/extensions.py.premutation`, verified
   byte-identical by SHA-256, and the suite re-ran green.

## Near-the-line statements (stated plainly, not re-judged)

- **Payload plane (725)** closes `built` as custody records,
  not as storage. The substrate structurally cannot store the
  archived content — the founding core-boundary decision is
  "metadata, never payloads" — so the byte plane itself is not
  and cannot be here. What the substrate honestly carries is
  the plane's custody accounting (who reports holding the
  bytes, how many, under what checksum reference, and whether
  the report matches the recorded size), and that is what was
  built, labeled `content_held_here: False` on the record
  itself. The parent may re-token this entry `reference` if it
  judges the accounting form insufficient; the build form
  would not change.
- **Encryption engine (728)** closes `built` as profile
  records for the same reason in the other direction: the
  entry's own text bounds it ("the build performs no
  cryptography — its custody records are Core"), and the
  records form over those Core custody records is exactly
  what the entry names as buildable. No operation in this
  module encrypts or decrypts anything, and the record says
  so (`encrypted_here: False`).

## Not covered

- No HTTP surface was added for the extension records (the
  sibling batch units' store-level pattern); the core REST API
  is untouched.
- No payload byte, key material, message content, or free-text
  query exists anywhere in this unit — by design, and pinned
  by the tests above.
- The sibling singleton `Storage|L3-adjacent` is a different
  unit; nothing here pre-builds its tier uplift.
