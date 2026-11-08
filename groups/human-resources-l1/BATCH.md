# Final GAPS batch, first unit — Remainder Singleton 62, Human Resources L1

Unit: the 1 OPEN entry in GAPS.md under "Remainder Singleton 62 —
Human Resources L1 (1 fork)" (inventory idx 713). This directory
had no prior batch unit, so the unit lands with first-unit naming
(`src/hr/extensions.py`, `tests/test_gaps_batch.py`, this note).
Disposition per `../../gaps-batch/DECISION.md` (ratified
2026-11-07): **1 build-extension — closed exactly as triaged in
`../../gaps-batch/inventory.json`: 1 built, 0 reference,
0 re-scoped, and no re-judgments.** The nearest-the-line call is
recorded below, with the grounds for keeping the drafted token.

All extension code is in one new module, `src/hr/extensions.py`
(`HrExtensions`, wrapping the core `HrStore`); every existing
module is byte-identical to its pre-unit state (SHA-256 verified
against the pre-work baseline in `scratch/prebatch-src.sha256`;
`store.py` still hashes to the shipped `ec34ab5e…`). Full suite:
91 tests before, **120 tests after, OK**, including the fresh
mutation-verified negative control recorded in
`tests/README.md` (the coverage-derivation mutant: 120 ran,
exactly 6 failures under mutation, restored and re-verified).

## The entry and its form

| Entry (GAPS.md text, idx) | Disposition | Built (module: `hr/extensions.py`) |
|---|---|---|
| Workforce scheduling & call-scheduling engine: the fork's whole function (deciding who works when, in advance, for healthcare organizations) — it matches none of the category's 25 families and is named here rather than forced into one; the automation machinery behind the fork's one claim is this engine's, not a separate item (713) | built | `create_shift_definition` / `get_shift_definition` / `list_shift_definitions` (`shf-`, kind label from a fixed vocabulary — day/evening/night/call — plus start/end clock labels validated as HH:MM data and recorded verbatim; no duration is ever computed from a label; the record carries `definition_only: True` and `generated_here` / `optimized_here: False`); `create_rotation` / `get_rotation` / `list_rotations` (`rot-`, bound to a core position, which is never modified; the caller's ordered `person_refs` held as data, each required to name a core person, duplicates and empty lists rejected, deep-copied at the boundary; the record carries `generated_here` / `optimized_here` / `automated_here: False` and its stored key set is pinned free of any coverage/status key); `record_roster_assignment` / `cancel_roster_assignment` / `get_roster_assignment` / `list_roster_assignments` (`ros-`, one date + one shift definition + one core position + one opaque `person_ref`, entered by the caller with `source: "recorded"` and `decided_here` / `assigned_automatically` / `optimized_here: False` on its face; a duplicate active assignment for the same person, date, and shift is refused whole with no id consumed, and re-recording is allowed once the earlier assignment is cancelled; cancellation is a recorded flag, never a deletion); `rotation_view` — for each shift definition, the pair state derives at read through the `_derive_pair_state` seam from the recorded assignments matching the rotation's position, the shift, the date, and rotation membership (cancelled and non-member assignments never fill a pair, both pinned); `schedule_summary` — counts over the scheduling records derived at read (`method: deterministic_counts`), gated on `report_read`. |

**The nearest-the-line call, stated plainly.** The entry names
an engine — deciding who works when — and the drafted
build-extension token was kept only for the records half of that
substance, on this category's own precedents: Untiered Set 16
(idx 907) closed its *resource scheduling engine* entry built
with schedule assignments held as data and `assigned_automatically:
False`, and the L2 remainder addition (idx 607) closed a *tracking
engine* built as records whose figures derive at read. What is
built here is exactly that grammar: definitions as data and
caller-recorded assignment records over opaque references, with
every derived figure a count or a state over the recorded
records. The engine's own machinery — schedule construction,
coverage optimization, call-rotation generation, and the
automation the fork's one claim names — is **not** built and is
stated absent on every record's face (`generated_here` /
`optimized_here` / `automated_here` / `decided_here` /
`assigned_automatically: False`) rather than absorbed into the
records' names; no method on the surface generates, expands,
optimizes, or auto-assigns anything, and a test pins that a
recorded assignment changes no core record. The alternative —
re-judging to reference — was considered and rejected on the
precedents above: unlike a device dispatch or a message send,
an assignment is a record in a database, and this substrate can
hold it without claiming the act that produced it. The build is
identical under either token.

**Privacy note (the spec's own bite, carried).** The founding
spec records that this fork's real records are rosters of named
clinicians with their shifts, and that the substrate holds
neither names nor schedules. The extension holds that line: a
roster assignment names a person only by opaque `person_ref`,
states nothing about identity, and no view assembles a named
roster; the core privacy test's forbidden-key set is walked over
every extension record and view, no public method accepts a
name-, identifier-, or content-shaped parameter (signature scan,
no `**kwargs` anywhere), and smuggled `name=` / `email=` /
`salary=` / `content=` keyword arguments raise `TypeError`.
Employee scope follows the core: assignments are person-bound
and employee-scoped; rotation definitions are visible to an
employee only when they are a member.

Cross-cutting, per the group's doctrines: RBAC rides the core's
fixed action set (mapping stated in the module docstring),
enforced before any state change or id allocation, so failed
operations consume no id and change nothing; successful
extension mutations audit on the core log with `ext_`-prefixed
actions; L1 tier discipline is held — the core's plain
append-only audit and four-role matrix ride as they are, with no
hash chain, lockout, or other higher-tier apparatus imported.
The surface is store-level only: the HTTP service and CLI are
unchanged, and no core module was modified for this unit.
