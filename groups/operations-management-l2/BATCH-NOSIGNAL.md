# Final GAPS batch — No-Signal Addition, Operations Management L2

Unit: the 2 OPEN entries of the "No-Signal Addition —
Operations Management L2 (SMX Elevate IAP, F1603077867)" section
in the repo-root GAPS.md (inventory idx 969–970). This is a
THIRD batch unit in this group directory: the first unit (the
original Group 36 section) shipped in `src/opsmgmt/extensions.py`
and the second (the Remainder Addition section) in
`src/opsmgmt/verticals.py`; both modules, and all seven
pre-existing core modules, stay **byte-identical** here
(SHA-256 verified before and after against
`scratch/prebatch-nosignal-src.sha256`; `store.py` remains
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
`extensions.py` remains
`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`,
`verticals.py` remains
`8fb9943f0680f74abfad35d9e9ca9483cdaee14f598dfd5e550fe1be1be8131b`).
The "Group 36 — Operations Management L2" and "Remainder
Addition — Operations Management L2" sections are different
units; nothing in them is touched or absorbed here.

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/opsmgmt/extensions_nosignal.py` (class `OpsNoSignal`,
wrapping the core `OpsStore`, audit prefix `extn_`), plus
`tests/test_gaps_batch_nosignal.py`.

**No-signal discipline.** This fork (SMX Elevate Intelligent
Automation Platform (IAP), F1603077867, FedRAMP Moderate / PaaS)
was left unclassified by the remainder census — its marketplace
description carries no citable function sentence — and was
resolved to this group by the live-docs research pass on SMX's
own capability sheet (ADDENDUM.md section 8). It claims **zero
families** under the group's taxonomy applied verbatim. The two
surfaces below are built ONLY from what the section's
registered entries and the addendum's gap notes name —
provisioning, monitoring, security, and lifecycle management of
multi-cloud platforms run as code, and built-in compliance
automation with policy guardrails over the baselines the fork
names in its own words — nothing inferred from the vendor's
reputation or from its third-party ISV catalogue (excluded at
spec time under the group's own discipline, and excluded here).

Group discipline, applied to every entry: this build is the
shared records substrate only. Nothing in the extension
provisions, operates, monitors, secures, lifecycle-manages,
automates, evaluates, or enforces. All `*_ref` parameters are
opaque tokens — whitespace, URL, hostname, and IP-shaped values
are rejected at the boundary — and links into the core
substrate use core ids validated through the core store. RBAC
reuses the founding 16-action matrix with no new actions
(mapping table in the module docstring); successful mutations
audit as `extn_*` actions on the core log, denied attempts as
`extn_*:denied`.

## Per-entry dispositions

### Stub-engine (1) — labeled reference implementation

1. **Cloud platform operations & lifecycle management engine**
   (idx 969; drafted `stub-engine`, closed as drafted) —
   `register_cloud_platform_reference` /
   `record_lifecycle_operation_reference` /
   `list_cloud_platform_references` /
   `list_lifecycle_operation_references` /
   `cloud_platform_summary`. Platform reference records over
   opaque references, with cloud labels held as data and
   automation modes validated against the modes the fork's own
   documentation names (Infrastructure-as-Code,
   Operations-as-Code, Policy and Compliance-as-Code — the
   research pass's notes in ADDENDUM.md section 8) and held as
   data, never executed; plus lifecycle operation references
   (provisioning / monitoring / security / lifecycle) whose
   statuses and counts are stored exactly as reported by an
   external operations engine. Every record carries
   `reference_stub: True`, with `provisioned_here`,
   `operated_here`, `monitored_here`, `secured_here`,
   `lifecycle_managed_here`, `performed_here`, and
   `executed_here` all `False`. The summary is derived counts
   only (platforms, operations by kind and by reported
   status), never stored. This surface is adjacent to, but not
   the same as, the first unit's platform-service references:
   those are references to the shipped union's
   connectivity/hosting services (MCSS-shaped); these are
   references to a multi-cloud platform operations engine and
   its lifecycle operations (SMX-shaped), the distinction the
   addendum's gap note itself draws.

### Build-extension (1) — records form in `opsmgmt.extensions_nosignal`

2. **Built-in compliance automation & policy guardrails engine**
   (idx 970; drafted `build-extension`, closed as drafted) —
   `register_baseline_pack` / `create_guardrail` /
   `record_guardrail_check` / `get_baseline_pack` /
   `list_baseline_packs` / `get_guardrail` / `list_guardrails`
   / `list_guardrail_checks` / `guardrail_view` /
   `compliance_summary`. Baseline pack records keyed to
   exactly the baselines the fork names in its own words
   (CMMC, HIPAA, HITECH, CJIS, PCI, SOC 1/2, FedRAMP, and DoD
   IL baselines, per ADDENDUM.md section 8), with control
   references held as data; guardrail definition records whose
   `rule_text` is held verbatim and never evaluated, scoped to
   the operations the fork's own gap note names
   (`multi_tenant` / `cross_domain`, plus `single_tenant` /
   `other`); and guardrail check records whose outcomes are
   stored exactly as an external compliance automation
   reported them. Every record carries `automated_here: False`
   and `enforced_here: False` (checks also `evaluated_here:
   False`) — the automation and the enforcement are the
   engine's, not this build's. `guardrail_view` derives the
   check count, the counts by outcome, and the latest reported
   outcome at read; the stored definition carries no count and
   no outcome (pinned by test). `compliance_summary` is counts
   only — a test pins that no score/rate/grade/percent key
   appears in it. Load-bearing guard: a guardrail check's
   recorder may never be the guardrail's definer, enforced at
   the named seam `_check_checker_not_definer` — this unit's
   fresh negative control. This surface is distinct from the
   first unit's same-words surfaces, and the distinction is
   recorded rather than elided: its generic policy
   definitions/evaluations are the MCSS policy enforcement
   plane's records (project policies, no baseline content),
   and its governance framework references are labeled stubs
   for the MCSS console engine; this entry is the SMX
   baseline-content automation — packs keyed to named
   compliance baselines with guardrails over multi-tenant and
   cross-domain operations — which is why the baseline-pack and
   guardrail records are genuine substrate work here while the
   console engine there shipped labeled.

## Re-judgments

None. Both entries fit their drafted dispositions on a close
reading of ADDENDUM.md section 8: the cloud platform
operations entry names an engine over external systems
(provisioning, monitoring, and lifecycle management of
platforms this build does not run, executed as code), so it
ships labeled exactly as drafted; the compliance automation
entry's honest records form — baseline packs as data,
guardrail definitions as data, check outcomes as reported —
is the same form this group's founding spec and first batch
unit gave the policy family (definitions Core-as-registry,
execution Extended), so the drafted build-extension stands,
with the automation itself stated absent on every record
rather than performed. Per DECISION.md qualification 1 the
alternative tokens were considered for both and neither fits
better: a `built` token for idx 969 would claim an operations
engine, and a `reference` token for idx 970 would misstate
records work this substrate genuinely performs.

Already-registered gaps gaining substance from this fork —
the authorization service / identity gap, AI models, and
platform-layer multi-tenancy, noted in ADDENDUM.md section 8 —
are NOT part of this unit: they were closed under their own
sections / the platform-layer decision and are not re-closed
here.

## Tests and negative control

- Suite: **228 before → 249 after, OK** (21 new tests in
  `tests/test_gaps_batch_nosignal.py`, at least one per entry,
  plus cross-cutting RBAC/audit, no-id-on-failure, and
  copies-are-copies pins). All pre-existing modules — core and
  both prior batch units' modules and tests — are
  byte-identical (SHA-256 verified) and their tests pass
  unchanged.
- Fresh mutation-verified negative control: the
  checker-not-definer guard `_check_checker_not_definer` in
  `src/opsmgmt/extensions_nosignal.py`. The in-test control
  (`TestCheckerNotDefinerNegativeControl`) asserts the
  canonical expectation, that a no-op mutant of the seam would
  not produce it, and that treating the mutant's outcome as
  expected fails. Live drill on the real file: a copy was
  saved to `scratch/extensions_nosignal.py.premutation`
  (pre-mutation SHA-256
  `709f2c1d768ea185b6537e03d893601257bb29eb9742f844688392c80d6ac155`,
  `scratch/extensions_nosignal.py.sha256`), the guard's
  condition was patched to `False` (guard disabled), and the
  full suite was re-run: **249 tests ran, exactly 2 failed** —
  `test_gaps_batch_nosignal.TestGuardrails.test_definer_may_not_check_canonical`
  and
  `test_gaps_batch_nosignal.TestCheckerNotDefinerNegativeControl.test_checker_guard_canonical_but_mutant_not`
  — which is the expected failure set for a disabled
  checker guard (every other test still passes against the
  mutant, as expected). The file was restored from
  `scratch/extensions_nosignal.py.premutation` and verified
  SHA-256 identical, and the suite re-ran green. Recorded in
  tests/README.md; raw drill output in
  `scratch/gaps_nosignal_mutation_run.txt`.

## Unresolved

Nothing unresolved within this unit. The no-signal surface is
a store-level surface only, matching the batch pattern for
sibling units: no HTTP routes were added (the founding
`service.py` is a core module and stays byte-identical), so
the extension is consumed in-process, like the other groups'
batch extensions.
