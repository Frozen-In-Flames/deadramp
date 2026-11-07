# Final GAPS batch — Cybersecurity & Risk Management (Untiered Set 1)

Batch note for the thirteen open entries of the repo-root
`GAPS.md` section "Untiered Set 1 — Cybersecurity & Risk Management
(27 forks, tier null)", closed under the ratified triage in
`gaps-batch/DECISION.md`. This set is untiered: tier stays null
everywhere, no baseline is asserted, and no CMMC equivalence is
drawn. The founding category discipline binds throughout —
defensive substrate only; nothing scans, detects, enforces,
blocks, trains, monitors, hosts, or executes.

## What was added

- `src/cyber/extensions.py` (one new module):
  `ExtensionStore`, the records-form register for the Extended
  families, in the exact shape of the sibling Cybersecurity L2
  batch extension (this set's core is that core, carried
  byte-identical): in-memory collections, validation before
  mutation (failed operations consume no id), founding-permission
  RBAC with denials audited under a `:denied` suffix, opaque
  references only (IP/URL/hostname-shaped values rejected at the
  boundary), derived-never-stored views, and counts-only rollups.
  Where a family was built as a records form in only one sibling
  (DLP, proofing), this module takes that sibling's records form.
- `tests/test_gaps_batch.py`: 22 tests pinning the extension
  surface entry by entry, including the stub/transport labels and
  a counts-only posture pin (recursive key scan).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control (below).
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (sha256 verified against
the founding accounting in the group README before and after the
build). No core change was needed.

## Per-entry disposition

**Build-extension (11)** — each closed by its in-substrate records
form: a registry of the thing, ingestion records for its output,
and tracking workflows around it.

1. **AI / ML security engines (13 claimants)** — model registry
   (`register_model_reference`) plus records of engine-reported
   output (`record_model_output_reference`). Per the ratified
   instruction for this unit, the records carry the siblings'
   honesty labels unchanged — `reference_stub: true` on both the
   model and output records — and labels are stored as reported:
   no model is loaded, no inference runs, no score is produced.
   Only the closure token differs from the sibling units, per the
   triage.
2. **SOAR / response automation execution (7)** — playbook
   reference records plus run reference records (same label
   treatment as entry 1): `reference_stub: true` throughout and
   `executed: false` on every run record. No playbook executes
   here, ever.
3. **Endpoint management agents (5)** — management-agent registry
   with declared capabilities from a closed vocabulary, plus
   reported patch-status records (`applied_here: false`);
   statuses stored as reported.
4. **EDR / XDR platforms (4)** — agent enrollment registry plus
   reported health-status records; the agent record's last status
   is the latest report, updated at record time.
5. **Threat intelligence platforms (3)** — feed registry plus
   ingestion records of feed-reported items; the reported level is
   stored as reported (this build computes no score for it), with
   a new → reviewed → retired lifecycle and derived counts by
   indicator kind.
6. **Network enforcement planes (3)** — enforcement-point
   registry (kind, opaque scope ref, opaque policy ref) with a
   register/retire lifecycle and a derived coverage view (counts
   by kind). Nothing is enforced.
7. **Insider-risk / DLP engines (3)** — the records form the L3
   sibling shipped for this family: DLP policy records whose
   declared-action vocabulary is `monitor` / `alert` only (an
   enforceable action is not representable), ingestion records of
   engine-reported events with the engine's own classification,
   and a derived summary bucketing events by classification.
   Counts only; no content is inspected.
8. **Identity proofing & fraud engines (2)** — proofing case
   records plus declared-outcome records, in the L3 sibling's
   form: the outcome is recorded by an actor other than the case
   opener, enforced by the `_check_outcome_recorder_not_opener`
   seam (the batch's mutation target, below), and the case view
   derives its current outcome at read time, never stored. The
   records are not identity evidence and this build is not an
   identity provider (PLATFORM-LAYER.md decision 1).
9. **CSPM / CNAPP / SSPM platforms (2)** — posture-engine
   registry plus count snapshots: a snapshot is a mapping of
   category name to non-negative integer count, exactly as
   reported; non-count values are rejected. The aggregate view
   sums counts per category at read time. Counts only — no
   posture score, rate, or grade exists anywhere in the view
   (pinned by a recursive key scan in the tests).
10. **Application security testing engines (2)** — testing-engine
    registry plus records of externally run tests
    (`executed_here: false`) carrying the finding count the engine
    reported; the findings themselves belong in the core register.
11. **Phishing simulation & training platforms (2)** — campaign
    records (`messages_sent: false` on every campaign; this module
    sends and simulates nothing) with a planned → approved →
    completed/cancelled lifecycle, training assignments keyed by
    opaque learner references (PII-shaped references are rejected
    at the boundary), and derived per-campaign counts by
    assignment status.

**Stub-engine (2)** — labeled reference implementations, records
only.

12. **Identity provider products (8)** — identity product
    reference records: `reference_stub: true`,
    `hook_only: true`, and `identity_provider: false` stated in
    the record's own fields, describing where an external identity
    product plugs in (PLATFORM-LAYER.md decision 1). This build
    authenticates no one and provides no identity service.
13. **Log / telemetry pipelines (3)** — pipeline reference
    records (`reference_stub: true`) plus transport receipts
    attesting that an external pipeline reports having moved a
    batch; every receipt carries `reference_stub: true` and
    `reference_transport: true`. No events flow through here.

## Re-judgments

None. All thirteen entries fit their triage dispositions in this
set's substrate; no entry was re-judged, and no core change was
required.

## Verification

- Full suite: 200 tests before the batch, **222 tests after, OK**
  (22 new tests in `tests/test_gaps_batch.py`).
- Fresh mutation-verified negative control: the
  recorder-blind proofing outcome guard (see `tests/README.md`).
  Mutating `_check_outcome_recorder_not_opener` so it never fires
  produced **exactly 1 failure in 222** — the canonical
  separation-of-duties pin — and the restored module (sha256
  verified identical to the pre-mutation copy) returns the suite
  to green.
- Core integrity: all eight `src/cyber/` core modules sha256-match
  the founding build's accounting recorded in the group README,
  before and after the build.
