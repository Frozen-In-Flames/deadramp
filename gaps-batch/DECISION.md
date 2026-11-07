# Final GAPS batch — disposition decision (ratified 2026-11-07)

Draft triage shipped 2026-10-31 as batch working state (commit db7a964):
1,022 open entries in GAPS.md, assigned to 494 clusters in
gaps-batch/inventory.json, with a per-entry disposition proposal:

- 626 entries — build-extension: records/derivation-shaped functions,
  built as in-substrate extensions of the owning group.
- 357 entries — stub-engine: engines over external systems, shipped as
  labeled reference implementations, following the house precedent
  (records carry `reference_stub: true` or `reference_transport: true`;
  nothing claims to execute against a real external system).
- 36 entries — rescope-platform: closed by one written platform-layer
  decision (PLATFORM-LAYER.md at the repo root), applied per group.
- 3 entries — rescope-written: entries whose own text bounds them as
  not buildable in a records substrate (staffed services, media
  transport), closed in writing with the bound stated.

On 2026-11-07 Aries directed: check where DeadRamp stands and
continue. That direction ratifies the split above as drafted. The
batch therefore proceeds on it, with two standing qualifications from
the draft itself:

1. Triage is pattern-based and is re-judged per unit at build time. If
   a unit's entries do not fit their drafted disposition on a close
   reading of the owning group's spec, the unit records the corrected
   disposition and its grounds in its BATCH.md; the inventory is a
   proposal record, not a gag.
2. An entry closes only when its disposition lands: built and tested,
   shipped as a labeled reference implementation, or re-scoped in
   writing. In GAPS.md a closed entry's status token changes from
   `open` to `built`, `reference`, or `re-scoped`; the entry text is
   never edited and an entry never disappears silently.

## Build pattern (per unit)

- One unit = one GAPS.md section = one group directory.
- Extension code lands in the owning group's `src/` as new module(s);
  existing core modules stay byte-identical unless a genuine core
  extension is required, in which case BATCH.md says why.
- Stub engines ship as labeled reference implementations inside the
  same extension surface, records only, never execution.
- Tests: the group's full suite must pass, plus a new test module
  pinning the extension surface and at least one fresh
  mutation-verified negative control for the new code (the group's
  signature drill re-run counts only when no new core function lands;
  extension code always lands, so the control is fresh), recorded in
  the group's tests/README.md.
- Each unit writes BATCH.md in its group directory: per-entry
  disposition, what was built for it, and any re-judgment under
  qualification 1.
- Builders do not commit. The parent re-verifies (membership of the
  unit's entries against gaps-batch/inventory.json, full suite re-run,
  a live smoke of the extension surface, mutation drill spot-check),
  closes the entries in GAPS.md, updates the README coverage/status
  text if it names gap state, and ships.

## Order

Units are worked largest-first by build-extension count, two at a
time on independent group directories, parent ships serially. The
re-scope closures (39 entries) landed first, in the same commit
family as this decision, because they need no build.
