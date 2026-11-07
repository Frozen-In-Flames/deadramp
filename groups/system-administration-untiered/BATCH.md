# BATCH — Untiered Set 10, System Administration (4 forks, tier null)

Final GAPS batch unit for the GAPS.md section **"Untiered Set
10 — System Administration (4 forks, tier null)"** (inventory
idx 839–845; the section's eighth entry, idx 846 "Platform
layer", was already closed `re-scoped` under PLATFORM-LAYER.md
and is untouched here). Dispositions follow
`gaps-batch/DECISION.md`; **no entry was re-judged** — every
entry fit its drafted disposition in the records form below,
read against this group's own spec (`UNION-SPEC.md`).

**Tier discipline, restated for this unit:** the set is
untiered — every member's FedRAMP impact level is Unknown in
the source — so the extension asserts no tier, no CMMC
equivalence, and no control baseline, and no record shape on
the new surface has a key that could hold one (pinned by the
recursive tier-null scan in the batch tests).

## What landed

- **New module:** `src/sysadmin/extensions.py` —
  `SysadminExtensions`, a wrapper around the core
  `SysadminStore`. All 7 pre-existing core modules are
  byte-identical to the shipped build (`store.py` still
  SHA-256 `46c4f2dc…`; the full table in README.md re-verified
  after the build).
- **New tests:** `tests/test_gaps_batch.py` — 47 tests.
  Suite: **93 → 140, all passing** (see the baseline note
  below).
- Extension writes map to the core `enter` RBAC action and
  resolve the organization through the core store on every
  operation, so the membership boundary binds the whole
  surface; denied writes are audited with a `:denied` suffix
  and successful mutations with `ext_`-prefixed actions on the
  core audit log. Current states (service case) and a capacity
  pool's latest observation derive at read from append-only
  recorded records and are never stored; all summaries are
  counts only, pinned by the recursive tier-null + no-score
  key scan over every extension record, view, and summary.
- The adjacent Moderate build's forms were read where families
  overlap (its `addition.py` / BATCH-ADDITION.md: the
  observability reference stub, the reported-CI discovery
  form) and adapted to this set's tier-null discipline; no
  Moderate baseline language was carried with them.

## Baseline note — one pre-existing failure, era-rescoped

The suite stood at 93 tests with **one pre-existing failure**
before this unit touched anything:
`test_nosignal_addition.py`'s git-HEAD pin asserted HEAD holds
exactly 4 spec sheets, but the no-signal append has since
shipped, so HEAD holds 5. Per the batch's standing era-rescope
accommodation, the pin is scoped to its own era's slice
(HEAD's first 4 sheets deep-equal the working tree's first 4)
with the scoping disclosed in the test's docstring; the
comparison's strength is unchanged. That is the only edit to
any pre-existing file besides the two README appends, and it
is a test file, not a core module.

## Per-entry disposition

**idx 839 — "Observability & monitoring engines" —
stub-engine → `reference`.**
Labeled reference implementation, in the adjacent Moderate
build's form for this same engine family: telemetry-source
records (`obs-`, kinds metrics / traces / logs / events /
other) and reported observation records (`obr-`) holding the
platform's output as an opaque `report_ref` with a verbatim
outcome label. Every record carries `reference_stub: True`
and state `recorded_reference_only`; `observed_here: False`
and `sensed_here: False` throughout. No telemetry is
collected, no payload is held — the record shape has no field
that could hold one (a smuggled `payload=` argument raises
`TypeError`, pinned).

**idx 840 — "AI root-cause & predictive analytics" —
build-extension → `built`.**
Built in the prediction-records form (the GRC
prediction-records ruling: label-shaped engine outputs close
built as records, with the computation half stated absent):
analysis definitions (`anl-`, kinds root_cause / prediction /
correlation / other) held as data, plus reported analysis
records (`anr-`) bound to exactly one definition and one of
the extension's own telemetry sources, holding the engine's
output as an opaque `report_ref` and a verbatim outcome
label. `inferred_here: False` / `computed_here: False` on
both shapes; no field can hold analysis content or a numeric
confidence (smuggled `confidence=` / `content=` raise
`TypeError`, pinned). The built/reference line against idx
839 is the drafted one: collection/sensing is the stub;
analysis *records* over the substrate's own sources are the
records surface.

**idx 841 — "IT service management systems" —
build-extension → `built`.**
Service-case records (`svc-`, kinds incident / problem /
major_incident / service_request / other, optionally bound to
a core managed system) with append-only reported state labels
(`svcs-`); the stored case shape is pinned with no state key —
current state derives at read via the unit's derivation seam.
Major-incident coordination is case-link records (`svl-`)
to a `major_incident` case (self-links and duplicate links
refused; `coordinated_here: False`). Alerting is
alert-policy definitions (`alp-`) held as data
(`executed_here: False`) plus alert dispatch records
(`ald-`) in the transport-receipt form
(`reference_transport: True`, `dispatched_here: False`,
`delivered_here: False`). On-call is rotation definitions
(`ocr-`) held as data by opaque `schedule_ref`. Core's own
request/change records are untouched: this is the working
system's records surface beside them, not a replacement.

**idx 842 — "IT operations & asset discovery engines" —
build-extension → `built`.**
Discovery-job records (`dcj-`) plus inventory-item records
(`inv-`) held as **reported** data: an item record is a
report filed by the caller's agentless discovery tooling
against a job, not a scan result produced here
(`discovered_here: False`, `scanned_here: False` on jobs).
Dependency mapping is relationship records (`rel-`) between
reported items in one organization (self-relationships
refused). Signal correlation is reported signal records
(`sgr-`) plus caller-reported correlation links (`sgc-`)
between them (`correlated_here: False` on both — the
correlation is the tooling's assertion, recorded, never
performed). Item shapes carry opaque refs only; a smuggled
`ip_address=` raises `TypeError`, pinned.

**idx 843 — "Endpoint management operations" —
build-extension → `built`.**
Endpoint records (`end-`) known by opaque `endpoint_ref`
only — the pinned shape has no field for a hostname, address,
or credential (a smuggled `hostname=` raises `TypeError`).
Operation definitions (`opd-`, kinds patch / deploy /
diagnostic / remote_session / automation / other) held as
data, plus operation-run records (`opr-`) with verbatim
reported outcomes; `executed_here: False` throughout —
nothing is patched, deployed, or remotely connected to here.
A run may bind a core change record, per the union spec's
own bound ("patching rides Core's change records as records
only"); a test pins the core change record byte-identical
before and after a bound run is recorded.

**idx 844 — "Vulnerability detection & remediation
prioritization" — stub-engine → `reference`.**
Labeled reference implementation: scan-job records (`scj-`,
bound to a core managed system), finding records (`vfd-`)
holding severity as a verbatim reported label, and
remediation-priority records (`rmp-`) holding the engine's
reported priority label verbatim — one per finding, a second
report refused so the recorded priority is the one report on
file. Every record carries `reference_stub: True` and state
`recorded_reference_only`; `scanned_here: False`,
`detected_here: False`, `prioritized_here: False`. Detection
is sensing against live systems and prioritization is a
ranking the engine computes; this substrate holds the
reports and derives neither.

**idx 845 — "Capacity, optimization & chargeback reporting
engines" — build-extension → `built`.**
Capacity-pool records (`cap-`, optionally bound to a core
managed system), capacity-observation records (`cpo-`)
holding quantities exactly as reported — non-negative
integers only, floats and booleans rejected at the boundary,
a reported used quantity above the reported total refused
(`measured_here: False`). A pool's latest observation
derives at read from its append-only observations and is
never stored on the pool (pinned both ways).
Optimization recommendations are records (`opt-`) holding
an opaque `recommendation_ref` and a verbatim outcome label
(`optimized_here: False`). Chargeback/showback reports
(`cbr-`) hold the platform's reported amount in **integer
cents** verbatim (a float amount is rejected at the
boundary), `computed_here: False` / `charged_here: False`;
summaries are counts only and never sum or average reported
amounts — a total would be a figure no reporter reported.

## Fresh negative control (mutation-verified)

**Latest recorded state label wins.** The derivation seam is
`SysadminExtensions._latest_state_label`: a service case's
current state is its *latest* recorded label. In-suite
control (`TestLatestStateNegativeControl`, 3 tests): the
canonical expectation (open → resolved reads
`reported_resolved`) passes on the real class; an
earliest-label mutant subclass reads `reported_open` and is
shown to violate the canonical expectation via
`assertRaises(AssertionError)`. External drill on the real
`src/sysadmin/extensions.py` (seam patched to read
`state_records[0]`): **140 ran, exactly 4 failed** — the two
negative-control canonicals, the case derivation test, and
the ITSM summary counts test; no core test failed and the
mutant subclass test passes under the mutation by
construction, as constructed. File restored from
`scratch/extensions.py.premutation` and verified
SHA-256-identical (`469d8997…`, recorded in
`scratch/extensions.py.sha256`); suite re-ran **140, OK**.
Full record in `tests/README.md`.

## Re-judgments

None. All 7 entries landed at their drafted dispositions
(5 `built`, 2 `reference`).

## Not covered by this unit

The founding six operations gaps (managed administration
operations, provisioning & deployment operations, application
delivery & hosting runtime, virtualization engine,
HA network operation, third-party CSP hosting platforms) are
registered under the parent System Administration L2 group,
not this set's section, and are untouched by this unit. The
extension surface is store-level only, like the adjacent
builds' batch surfaces; the core HTTP API and CLI are
unchanged.
