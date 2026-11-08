# Final GAPS batch — Remainder Singleton 61, Health & Wellness L1

Unit: the 2 OPEN entries of the GAPS.md section "Remainder
Singleton 61 — Health & Wellness L1 (1 fork)" (inventory idx
711–712; the section header and the entry texts were read from
GAPS.md and `gaps-batch/inventory.json` and matched verbatim —
GAPS.md and the inventory agree on exactly 2 open entries, no
discrepancy), worked under `gaps-batch/DECISION.md` (ratified
2026-11-07) and `PLATFORM-LAYER.md`. Built 2026-11-08. The parent
re-verifies, closes the entries in GAPS.md, and ships; this file
records the per-entry dispositions and grounds.

## What was built

One new module, `src/health/extensions.py` — `HealthExtensions`,
a wrapper around the core `HealthStore` in the house pattern. All
7 pre-existing core modules are byte-identical to the shipped
singleton build (SHA-256 verified against a pre-build baseline
recorded in `scratch/prebatch-src.sha256`; `store.py` unchanged:
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`,
the shipped hash). No core change was needed or made. The HTTP
service layer is unchanged; the extension surface is a library
surface over the core store, as in the sibling units.

One new test module, `tests/test_gaps_batch.py` (20 tests).
Suite: **79 → 99 tests, all passing**.

## The section's bound, stated once

Both entries are this fork's own engines, named from its
description's own words — the product's actual surface. This
group's UNION-SPEC states the bound plainly: "These are
clinical/diagnostic surfaces: per this category's hard privacy
rule they are never built here, and nothing in this build claims
any diagnostic function." The substrate's shapes cannot hold a
sleep study, a test result, a device payload, or any clinical
signal; the build is not a medical device and claims no FDA
status (the fork's device clearance belongs to the fork's
product). Both entries therefore land as **labeled reference
implementations**: a registry of the external platform's reported
activity — dispatch, initialization, collection, and review
records against opaque references, every record carrying
`reference_stub: True` and state `recorded_reference_only`. Both
were drafted `build-extension`; both are **re-judged** to
reference, with grounds per entry below. This mirrors the sibling
tier's ruling for the identical shape: Singleton 46's batch unit
re-judged its two build-extension drafts to reference because the
fork's clinical engines have no records form that is the
function's own substance on a substrate that may not hold the
clinical content the function operates over.

The founding privacy discipline binds the extension absolutely:
records and opaque caller-supplied references only. No shape in
the extension has a diagnosis, clinical-note, name, contact,
date-of-birth, insurer, member-number, study-data, test-result,
finding, waveform, signal, or hardware-identifier field — those
fields do not exist, and the suite pins that with a recursive
forbidden-key scan over every record, view, and summary and a
`TypeError` pin on smuggled keyword arguments.

Tier discipline at L1 (the lightest tier) binds the form: the
extension writes to the core's plain append-only audit log
(`ext_`-prefixed actions, denied writes audited `:denied`); no
hash chain, no fail-closed audit machinery, and no lockout are
imported downward from Singleton 46, and the auditor keeps this
tier's core read set rather than the High tightening. RBAC uses
the core's existing actions, enforced before any state change or
id allocation; member scope mirrors the core store's.

## Per-entry dispositions

| idx | Entry (verbatim) | Drafted | Final | Closure |
|---|---|---|---|---|
| 711 | Home sleep-test dispatch & device initialization engine: dispatching home diagnostic devices to patients and initializing them (the fork's own headline function; the records substrate holds none of the device pipeline) | build-extension | **reference** (re-judged) | `reference` |
| 712 | Sleep study results collection & provider review: collecting study data and test results for clinician review — clinical content, Extended by construction in this category (the EEG singleton's precedent); the substrate cannot hold it, and its measurement records are caller-recorded administration values only | build-extension | **reference** (re-judged) | `reference` |

### idx 711 — RE-JUDGED build-extension → reference

Grounds: dispatching a device into a patient's home and
initializing it are acts on a physical device, performed by the
fork's platform — no derivation over registry records dispatches
or initializes anything, and the entry's own parenthetical
records that "the records substrate holds none of the device
pipeline." The substrate's records substance for the study itself
already stands in Core: the core-boundary decision carries the
study as a scheduled, completable event (Core 6 activity
records), so no core function presupposes a dispatch registry —
unlike the L2 unit's device links (idx 186, built), which are
presupposed by the measurement records the substrate holds. What
remains of this entry is the fork's device-pipeline engine, and
its honest in-substrate form is the reference registry: dispatch
references (`dsp-`, opaque `device_ref` — a second reference for
the same participant + device pair refused by the
`_check_dispatch_device_unique` seam — bound to a core
participant and optionally a core program,
`dispatched_here: False`, `initialized_here: False`) and
initialization outcome records (`ini-`, the external platform's
outcome label verbatim). The dispatch view derives
`outcome_count` and `latest_outcome_label` at read;
`dispatch_summary` is deterministic counts only.

### idx 712 — RE-JUDGED build-extension → reference

Grounds: the entry's substance is the study data and test
results themselves — clinical content, Extended by construction
in this category, and the entry's own text records that "the
substrate cannot hold it." Per the EEG singleton's precedent
(its idx 444: a function over clinical content the substrate may
not hold has no records form that is the function's own
substance), the honest in-substrate form is the collection/review
registry as a labeled reference: collection references (`col-`,
a study named only by an opaque `study_ref` in the external
system, a reported `record_count` and a date — never a payload,
result, or finding; `reference_transport: True`,
`content_held_here: False`, `collected_here: False`) and review
outcome records (`rvw-`, the reviewer's outcome label verbatim
as reported, `decided_here: False`, `interpreted_here: False` —
this build reviews nothing and decides nothing). The collection
view derives `review_count` and `latest_outcome_label` at read;
`collection_summary` is deterministic counts, its
`reported_records_total` stated as the sum of the collections'
reported counts — no study content is summed, because none is
held.

Totals: **0 built, 2 reference, 2 re-judged** (idx 711 and 712,
build-extension → reference, grounds above). Closure tokens for
the parent: both entries close `reference`.

## Negative control (fresh, for the new code)

Seam: `HealthExtensions._check_dispatch_device_unique` — the
single uniqueness check for dispatch references (a dispatch
reference names exactly one reported dispatch of a device to a
participant, so a second reference for the same participant +
`device_ref` pair is refused). In-test control:
`TestDispatchDeviceUniqueNegativeControl` (canonical refuses the
duplicate; the `_NoDispatchDeviceGuard` mutant subclass —
operating on the canonical instance's tables — accepts it,
leaving two dispatch references for one device; canonical
refuses again). Live mutation verified 2026-11-08: the seam's
scan line patched to iterate an empty dict on the real
`extensions.py` — **99 tests, exactly 2 failures**, both on the
duplicate-refusal surface (the duplicate-refusal test and the
control's canonical leg). Restored from
`scratch/extensions.py.premutation`, SHA-256 verified identical
(`4a8e03d73cdeb132569d41ee61d51cde2cc1631ca374208e9e6019ed3a1db95a`),
suite re-ran green. Full record in `tests/README.md`.

## Not covered by this unit

- The category's carried Extended set (clinical decision
  support, EMR/EHR integration, claims adjudication, device
  connectivity, AI/ML, automation, survey depth, engagement,
  telehealth, native apps, hosting) is registered once under
  Group 18 in GAPS.md and was closed by the L2 group's own batch
  unit; the three substance memberships named under this section
  (EMR/EHR integration engines, device connectivity / sync
  pipelines, multi-device native apps) gain this fork by
  substance only and are not this section's entries.
- The platform notes in this section's GAPS.md prose
  (multi-tenancy, encryption at rest, TLS, demo identities as
  hooks) are closed by `PLATFORM-LAYER.md` at the batch level,
  not by this unit; no extension record asserts a control family.
