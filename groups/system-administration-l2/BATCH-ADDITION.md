# BATCH-ADDITION — Remainder Addition, System Administration L2 (+8 forks)

Final GAPS batch unit for the GAPS.md section **"Remainder
Addition — System Administration L2 (+8 forks)"** (inventory idx
552–560). Dispositions follow `gaps-batch/DECISION.md` as drafted;
**no entry was re-judged** — every entry fit its drafted
disposition in the records form below, read against this group's
own spec (`UNION-SPEC.md` + `ADDENDUM.md` §5).

## What landed

- **New module:** `src/sysadmin/addition.py` —
  `SysadminAddition`, a wrapper around the core `SysadminStore`.
  This is the second batch unit in this directory; it follows the
  second-unit pattern (distinct module name, its own test module
  and this file). All 7 pre-existing core modules are
  byte-identical to the shipped build (`git diff HEAD -- src/`
  empty; `store.py` still SHA-256 `46c4f2dc…`), and no existing
  batch file existed in this directory to disturb.
- **New tests:** `tests/test_gaps_batch_addition.py` — 29 tests.
  Suite: **78 → 107, all passing.**
- Extension writes map to the core `enter` RBAC action and
  resolve the organization through the core store on every
  operation, so the membership boundary (the fork's
  contract-gated access claim) binds the whole surface; denied
  writes are audited with a `:denied` suffix and successful
  mutations with `ext_`-prefixed actions on the core audit log.
  Current states (ticket / asset / project / security case)
  derive at read from append-only recorded state labels and are
  never stored; all summaries are counts only, pinned by a
  recursive no-score key scan.

## Per-entry disposition

**idx 552 — Virtual workspace & desktop delivery platform
(Citrix DaaS) — build-extension → `built`.**
Workspace/desktop definitions held as data (`wsd-`, kinds
desktop / application / bundle) plus delivery-session records
(`dss-`) with verbatim reported outcomes and opaque user
references; every record carries `delivered_here: False` — no
session is brokered or delivered here. Summary derives counts
by kind and by verbatim outcome label.

**idx 553 — Observability & AIOps platform (Dynatrace) —
stub-engine → `reference`.**
Labeled reference implementation: telemetry-source records
(`obs-`) and reported insight records (`ins-`) holding the
platform's AI answers as opaque `report_ref`s with verbatim
outcome labels. Every record carries `reference_stub: True` and
state `recorded_reference_only`; sources carry
`observed_here: False`, insights `inferred_here: False`. The
insight record's key set is pinned — no field can hold insight
content.

**idx 554 — IT service & asset management suite, ITSM / ITAM
(OpenText; Oracle service desk rides it) — build-extension →
`built`.**
Service tickets (`tkt-`, kinds incident / problem /
service_request / change_request / other, optionally bound to a
core managed system) and asset records (`ast-`, kinds hardware /
software / license / peripheral / other) with append-only
reported state labels (`tkts-` / `asts-`); current state derives
at read via the unit's derivation seam, and the stored ticket /
asset shapes are pinned with no state key. Summary derives
counts by kind and by derived current state.

**idx 555 — Universal discovery & CMDB engine (OpenText) —
build-extension → `built`.**
Discovery-job records (`dcj-`) plus configuration-item records
(`cir-`) held as **reported** data: a CI record is a report
filed by the caller's discovery tooling against a job, not a
scan result produced here — every record carries
`discovered_here: False`. Service dependency mapping is
relationship records (`rel-`) between reported CIs in one
organization (self-relationships rejected). Summary derives
counts of jobs, CIs by reported kind, and relationships.

**idx 556 — Project & portfolio management platform (OpenText)
— build-extension → `built`.**
Portfolio records (`pfl-`) and project records (`prj-`,
optionally bound to a core managed system) with append-only
reported state labels (`prjs-`) and current state derived at
read. `portfolio_view` returns the portfolio, its projects with
derived states, and counts by current state — **no portfolio
score, ranking, or investment-optimization value is computed
anywhere**, pinned by the recursive key scan (scenario planning
and investment optimization are the vendor engine's outputs and
are not reproduced; the records the function presupposes are
what closes here).

**idx 557 — DEX analytics & endpoint automation platform
(TeamViewer) — build-extension → `built`.**
Endpoint-experience reports (`dxr-`) held verbatim: the
reporting platform's own assessment, including any vendor
experience score, arrives inside the verbatim `experience_label`
text and is **never computed, averaged, or re-derived here**
(`computed_here: False`; a numeric label is rejected at the
boundary, pinned by test). Endpoint automation ships as
definitions held as data (`dxa-`) plus automation-request
records with verbatim outcomes (`dxq-`), `executed_here: False`
on both — per the house doctrine the registry never executes.

**idx 558 — Geospatial (GIS) application platform (Esri's
ArcGIS payload) — build-extension → `built`.**
Dataset records (`gis-`, metadata only) and layer records
(`lyr-`) carrying an opaque `geometry_ref` only, plus reported
hosted-service records (`gsv-`). Every record carries
`rendered_here: False` (services also `hosted_here: False`).
No entity shape has a field that can hold geometry or
coordinate content — pinned by exact key sets, the recursive
scan, and a test showing a smuggled `geometry=` keyword raises
`TypeError` at the signature.

**idx 559 — Managed backup & disaster-recovery services
(Contegix, DLH, Oracle, Esri) — stub-engine → `reference`.**
Labeled reference implementation: backup-job records (`bkj-`,
bound to a core managed system), backup-outcome records
(`bko-`) with verbatim outcome labels and the service's own
reported byte counts carried as reported data, and
restore-request records (`rst-`) with verbatim outcomes. Every
record carries `reference_stub: True` and state
`recorded_reference_only`; `backed_up_here: False` /
`restored_here: False` throughout. Retention enforcement is
**not** performed or claimed here: it is the embedding
organization's records schedule at the deployment layer
(PLATFORM-LAYER.md decision 4).

**idx 560 — Security operations services: SOC / SIEM /
vulnerability scanning (Esri, Contegix, DLH) —
build-extension → `built`.**
Security-case records (`sec-`, kinds alert / incident /
vulnerability / other, optionally bound to a core managed
system) with append-only reported state labels (`secs-`) and
current state derived at read, plus finding records (`sef-`)
held verbatim: severity is a reported label, never a computed
value, and no scanning or detection happens here
(`scanning_here: False`, `detected_here: False` on findings;
`detected_here: False` on cases). This stays inside this
group's own records doctrine — findings are reports of the
operating service's work; no other category's scoring or
detection form is imported. Summary derives counts by kind,
derived current state, and verbatim severity label.

## Fresh negative control (mutation-verified)

**Latest recorded state label wins.** The derivation seam is
`SysadminAddition._latest_state_label`: a record's current
state is its *latest* recorded label. In-suite control
(`TestLatestStateNegativeControl`, 3 tests): the canonical
expectation (open → resolved reads `reported_resolved`) passes
on the real class; an earliest-label mutant subclass reads
`reported_open` and is shown to violate the canonical
expectation via `assertRaises(AssertionError)`. External drill
on the real `src/sysadmin/addition.py` (seam patched to read
`state_records[0]`): **107 ran, exactly 6 failed** — the two
negative-control canonicals, the ITSM derivation and
summary-counts tests, the portfolio derived-state counts test,
and the security-case derivation test; no core test failed and
the mutant subclass test passes under the mutation by
construction, as constructed. File restored from
`scratch/addition.py.premutation` and verified SHA-256-identical
(`scratch/addition.py.sha256`); suite re-ran **107, OK**. Full
record in `tests/README.md`; raw failing set in
`scratch/addition_mutation_run.txt`.

## Re-judgments

None. All 9 entries landed at their drafted dispositions
(7 `built`, 2 `reference`).

## Not covered by this unit

The founding section's own batch entries (Singleton 54 —
System Administration L2) are a different GAPS.md section and a
different unit; the six Extended gaps the singleton registered
(managed administration operations, provisioning operations,
delivery/hosting runtime, virtualization engine, HA network
operation, CSP hosting platforms) are untouched by this unit.
