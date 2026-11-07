# BATCH-SINGLETON — Singleton 54, System Administration L2 (1 fork, new category)

Final GAPS batch unit for the GAPS.md section **"Singleton 54 —
System Administration L2 (1 fork, new category)"** (inventory idx
515–520). Dispositions follow `gaps-batch/DECISION.md` as drafted;
**no entry was re-judged** — every entry fit its drafted
disposition in the records form below, read against this group's
own spec (`UNION-SPEC.md`, whose gap list names these six from the
founding fork's own verbs). These are the founding fork's own
operations — the work and engines behind the records Core already
holds — and per the founding doctrine they close as records ABOUT
those operations, never the operations themselves: this build
administers no live system, patches nothing, provisions nothing,
and performs no management work.

## What landed

- **New module:** `src/sysadmin/singleton_extensions.py` —
  `SysadminSingletonExtensions`, a wrapper around the core
  `SysadminStore`. This is the third extension surface in this
  directory (after the founding core and the remainder-addition
  unit's `addition.py`); it follows the second-unit pattern
  (distinct module name, its own test module, this file). All 8
  pre-existing `src/sysadmin/` modules are byte-identical to
  their shipped builds (verified against a pre-build SHA-256
  baseline; `store.py` still `46c4f2dc…`, `addition.py` still
  `5f4af2ab…`), and no existing batch file was disturbed.
- **New tests:** `tests/test_gaps_batch_singleton.py` — 31 tests.
  Suite: **107 → 138, all passing.**
- Extension writes map to the core `enter` RBAC action and
  resolve the organization through the core store on every
  operation, so the membership boundary (the fork's
  contract-gated access claim) binds the whole surface; denied
  writes are audited with a `:denied` suffix and successful
  mutations with `exts_`-prefixed actions on the core audit log.
  Current states (virtual instance, HA configuration) derive at
  read from append-only recorded labels and are never stored;
  all summaries are counts only, pinned by a recursive no-score
  key scan. The adjacent tier-null build's forms were read where
  families overlap (its endpoint operation definitions and
  reported-data discovery form) and adapted to this group's
  Moderate baseline as its own docs state it.

## Per-entry disposition

**idx 515 — "Managed OS & services administration operations
(the full management itself)" — build-extension → `built`.**
Administration-operation definitions (`aod-`, kinds configure /
patch / harden / maintain / administer / other) held as data,
plus operation records (`aop-`) bound to a core managed system
with verbatim reported outcomes; every record carries
`executed_here: False`, operation records also
`operated_here: False`. Recording an operation alters no system
record (pinned by test). The full management itself remains the
operator's work, performed by its people and platforms elsewhere
— what closes here is the records surface that work presupposes,
beside Core's service-request and change records, not a
replacement for them.

**idx 516 — "System provisioning & deployment operations" —
stub-engine → `reference`.**
Labeled reference implementation: provisioning-job records
(`pvj-`) naming their target by an opaque `target_ref` — the
instance does not exist until the platform stands it up, so
there is no core system to bind — plus provisioning-outcome
records (`pvo-`) with verbatim outcome labels and the platform's
own reported instance count carried as reported data
(floats/bools/negatives rejected at the boundary). Every record
carries `reference_stub: True` and state
`recorded_reference_only`; `provisioned_here: False` /
`deployed_here: False` throughout.

**idx 517 — "Application delivery & hosting runtime" —
stub-engine → `reference`.**
Labeled reference implementation: hosting-profile records
(`dlp-`) bound to a core application, plus hosting-report
records (`dlr-`) with verbatim outcomes. Every record carries
`reference_stub: True` and state `recorded_reference_only`;
`hosted_here: False` / `delivered_here: False` throughout. The
runtime is the CSP's environment; per PLATFORM-LAYER.md
decision 6 the hosting substrate does not transfer to this
build, and Core's application registry already holds the
records form of the delivery claim.

**idx 518 — "Virtualization engine (the underlying cloud
provider's)" — build-extension → `built`.**
The engine itself is the CSP's and is not reproduced; what
closes here is the records surface it presupposes:
virtual-instance records (`vin-`) held as **reported** data,
carrying the same opaque `platform_ref` Core systems carry and
optionally bound to a core managed system, with append-only
reported state labels (`vins-`); current state derives at read
via the unit's derivation seam, and the stored instance shape is
pinned with no state key. Every record carries
`virtualized_here: False`. Summary derives counts by derived
current state. This is the same reported-data form the
remainder-addition unit used for discovery CIs, applied to the
founding fork's virtualization claim.

**idx 519 — "High-availability network operation" —
build-extension → `built`.**
HA configuration records (`hac-`) holding the operator's
redundancy arrangement as a verbatim label (for example
"active-passive"), optionally bound to a core managed system,
plus append-only reported availability event records (`hae-`,
labels reported_healthy / reported_degraded / reported_failover
/ reported_recovered). A configuration's current availability
state derives at read from its latest recorded event label.
Every configuration carries `operated_here: False` and
`failover_performed_here: False` — events are reports of the
operating network's behavior; recording one executes no
failover and operates no network. Summary derives counts by
derived current state and by verbatim event label.

**idx 520 — "Third-party CSP hosting platforms (outside the
fork's own boundary)" — stub-engine → `reference`.**
Labeled reference implementation: platform-declaration records
(`pld-`) naming the external platform by the same opaque
`platform_ref` Core systems already carry (unique per
organization), plus platform-report records (`plr-`) with
verbatim outcomes. Every record carries `reference_stub: True`
and state `recorded_reference_only`; `hosted_here: False` /
`operated_here: False` throughout. Grounded in PLATFORM-LAYER.md
decision 6: the platforms are outside the fork's own boundary
by its own statement, and their hosting substrate does not
transfer; this surface declares the platform relationship
itself, nothing more.

## Fresh negative control (mutation-verified)

**Latest recorded state label wins.** The derivation seam is
`SysadminSingletonExtensions._latest_state_label`: a record's
current state is its *latest* recorded label. In-suite control
(`TestSingletonLatestStateNegativeControl`, 3 tests): the
canonical expectation (an HA configuration labelled
`reported_healthy` then `reported_failover` reads
`reported_failover`; an instance labelled
`reported_provisioning` then `reported_running` counts under
`reported_running` in the summary) passes on the real class; an
earliest-label mutant subclass reads `reported_healthy` and is
shown to violate the canonical expectation via
`assertRaises(AssertionError)`. External drill on the real
`src/sysadmin/singleton_extensions.py` (seam patched to read
`state_records[0]`): **138 ran, exactly 5 failed** — the two
negative-control canonicals, the HA derivation test, the HA
summary-counts test, and the virtual-instance derivation test;
no core or addition-unit test failed, and the mutant subclass
test passes under the mutation by construction, as constructed.
File restored from `scratch/singleton_extensions.py.premutation`
and verified SHA-256-identical
(`scratch/singleton_extensions.py.sha256`); suite re-ran
**138, OK**. Full record in `tests/README.md`; raw failing set
in `scratch/singleton_mutation_run.txt`.

## Re-judgments

None. All 6 entries landed at their drafted dispositions
(3 `built`, 3 `reference`).

## Not covered by this unit

The remainder additions' own batch entries (idx 552–560) are a
different GAPS.md section and a different unit, already shipped
in `addition.py`; they are untouched here. The extension surface
is store-level only, like the addition unit's; the core HTTP API
and CLI are unchanged. Platform-layer items named in the
section's closing note (control inheritance from the underlying
CSP, encryption at rest, demo identities as hooks) stay closed
under PLATFORM-LAYER.md and are not re-opened by this unit.
