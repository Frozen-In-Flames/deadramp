# Final GAPS batch — Group 33, Governance, Risk, and Compliance (GRC) L2

Unit: GAPS.md section **"Group 33 — Governance, Risk, and
Compliance (GRC) L2 (2 forks)"**, 7 entries (inventory idx
353–359), worked per `../../gaps-batch/DECISION.md`. One new
module, `src/grc/extensions.py` (`GrcExtensions` wrapping the
core `GrcStore`), plus `tests/test_gaps_batch.py`. **All
pre-existing core modules are byte-identical** (SHA-256 checked
before/after, drill included; `store.py` still `e2eac653…`); no
service routes were added — the batch surface is store-level,
following the sibling batch units' pattern. Suite: **132 → 161
tests, all passing.**

The category doctrine binds every disposition below: **no
computed score, rating, grade, or percentage anywhere**.
Posture in this group is counts only, enforced by recursive key
scans; the extension surface is scanned the same way
(`TestExtensionInvariants`). One spelling consequence, stated
plainly: the founding scan forbids any key containing `score`,
so the boundary the batch brief spells `scored_here` is carried
on this group's records as `computed_here: False` — the same
statement (no value was computed here), in the only key form
this group's pinned invariant allows. Reported statuses,
outcomes, priorities, and values are recorded **verbatim**,
never computed; date-based figures are derived at read, never
stored. Extension mutations write to the core's append-only
audit log under `ext_` action names; denied attempts raise and
change nothing (auditing a denial at this store-level surface
is the HTTP layer's responsibility, exactly as in the core —
there are no extension HTTP routes).

## Per-entry dispositions

**Built (3):**

- **Vulnerability scanning engine (prioritization / scoring of
  findings; the core records findings and remediation
  verbatim)** (idx 355) — *built in scan-records form, not
  re-judged.* Scan-job records (`scanned_here: False`),
  scan-report records holding the scanner's reported outcome
  verbatim and its finding count **as reported**, and priority
  records holding a scanner- or assessor-reported priority
  label **verbatim** against a core finding
  (`prioritized_here: False`, `computed_here: False`).
  Test-pinned boundaries: a scan report creates no core
  finding, and recording a priority leaves the core finding
  byte-identical. Grounds for keeping the drafted `built`
  token, mirroring the sibling GRC L3-adjacent unit's
  prediction-records ruling (idx 419/421, shipped): the entry's
  own parenthetical assigns the records half to the core
  ("the core records findings and remediation verbatim"), and
  the buildable half of the entry is exactly that records
  surface, genuinely built and tested. The engine half — a
  scanner interrogating a live system, and any computation
  that *produces* a priority — is not here and is not
  claimed; had the entry required computing a priority from
  finding data, it would have been re-judged to reference on
  doctrine grounds. It does not: priorities arrive as
  reported labels, like severities and statuses everywhere in
  this core.
- **Posture / risk scoring engines (deliberately absent from
  the core; no aggregate is computed anywhere)** (idx 357) —
  *built in reported-value-records form, not re-judged.*
  `record_reported_value` stores a value an external scoring
  engine or assessor reported for a governed system
  **verbatim as a label**, with its reported scale label and
  reporter, carrying `computed_here: False`. Aggregates over
  the surface are counts of the recorded labels only.
  Test-pinned: the core posture summary is byte-identical
  before and after reported values are recorded — the core
  neither reads nor reflects them, so the UNION-SPEC sentence
  this entry quotes ("no aggregate is computed anywhere")
  remains true of the core, and of this surface. Grounds,
  again mirroring the L3 prediction-records ruling: a build
  that *computed* a posture or risk value would break the
  founding invariant and contradict the entry's own text;
  what the records substrate genuinely does — and what every
  engine's disposition in this group presupposes — is record
  the engine's reported outputs faithfully. That surface is
  built, tested, and bounded on every record.
- **FedRAMP authorization package generation** (idx 359) —
  *built.* Package records store **no figures at all**
  (exact key set pinned by test: requester, system, framework,
  note, and the two boundary labels `submitted_here: False` /
  `exported_here: False`). The manifest is a view derived at
  read from the core's records — authorization references with
  their current recorded statuses, assessment references, the
  framework's control count, and evidence / finding /
  indicator-result counts for the package's system, with the
  overdue figure derived through the core's own
  `derive_finding_status`. Test-pinned: the view tracks
  registry state (records added after the package was
  registered appear in its next view) while the stored package
  record never gains a figure. No document is generated,
  exported, or submitted; assembly of the submission artifact
  from these records is the embedding organization's step,
  stated on the record.

**Reference (4, labeled reference implementations, as drafted):**

- **Automated evidence-validation engine, incl. API /
  telemetry evidence collection** (idx 353) — collection-source
  records (definitions of API/telemetry sources,
  `reference_transport: True`, `collected_here: False`),
  validation-job records (`reference_stub: True`,
  `validated_here: False`), and validation-report records
  holding the engine's reported status verbatim. Test-pinned:
  recording a validation report leaves the core evidence
  record byte-identical — its recorded validation status is
  set only by a reviewer's core review operation.
- **Continuous-monitoring feeds & scanner integrations**
  (idx 354) — feed-definition records (`reference_stub: True`,
  `reference_transport: True`, `connected_here: False`,
  `ingested_here: False`) and feed-receipt records (status
  verbatim, count as reported; booleans, floats, and negative
  counts rejected at the boundary). Test-pinned: a receipt
  creates no core indicator result and no core finding.
- **Automated KSI validation** (idx 356) — validation-run
  records bound to a core indicator and system
  (`reference_stub: True`, `validated_here: False`,
  `evaluated_here: False`) and run-report records holding the
  engine's reported status verbatim. Test-pinned: a run report
  creates **no** core indicator result — core results are
  recorded through the core's own operation, by a person,
  exactly as the UNION-SPEC ruled ("Recording the result is
  Core; performing the validation automatically is Extended").
- **Hosted enclave & PaaS operations themselves (one sibling's
  own domain; also the other sibling's hosting claim)**
  (idx 358) — environment records over core governed systems
  (`reference_stub: True`, `hosted_here: False`,
  `operated_here: False`) and operation records holding
  reported operation kinds and outcomes verbatim, in the
  Communication adjudicated form. Platform layer per
  PLATFORM-LAYER.md decision 6: hosting and enclave operations
  are deployment properties and do not transfer to a records
  build; the records those operations presuppose are what is
  built here.

## Re-judgments

None. All 7 entries landed at their drafted triage tokens
(3 build-extension, 4 stub-engine). The two judgment calls the
brief flagged — idx 355 (scanning/prioritization) and idx 357
(scoring engines) — close as **built** in the records forms
above rather than as reference stubs, on the grounds stated
per entry: the sibling GRC L3-adjacent unit's shipped
prediction-records ruling for the identical shape, and this
group's own UNION-SPEC line that the Core records engine
outputs faithfully while the engines stay Extended. In both
cases the *computation* half of the entry remains absent by
doctrine and is stated as absent on every record
(`computed_here: False`); if the parent prefers the
`reference` token for either, only the token changes — the
code is identical either way.

## Long tail — named, not covered by this unit

- The **Remainder Addition — GRC L2 (+5 forks)** section's 7
  entries (policy lifecycle, agentic execution, AI narrative
  generation, ITSM, healthcare quality, connected reporting,
  and the addition forks' remaining Extended surfaces, per
  `ADDENDUM.md`) are registered under their own GAPS.md
  section and belong to that section's own unit. They are not
  absorbed here.
- The **Remainder Addition — GRC L3-adjacent** section's two
  entries and the **Singleton 44** section are other units,
  already shipped or separately registered; untouched.
- `risk_management` and `policy_management` were named
  absences at founding and were retired by the remainder
  additions' own claims (see `ADDENDUM.md`); nothing in this
  unit changes their record, and no score is computed for
  either — the additions carry them as records, as does this
  surface.
- The platform-layer paragraph of this group's GAPS.md
  section (encryption at rest, single-tenant deployment,
  IA-2 hooks) stands on PLATFORM-LAYER.md, closed in writing
  before this unit.

## Verification (coordinator's own run)

- Full suite **161/161 OK** on the coordinator's run (132
  before), plus a live end-to-end smoke exercising all seven
  entries' surfaces: engine report left the core evidence
  status `unvalidated`; feed receipt and KSI report created
  zero core findings/results; core posture totals unchanged
  by reported values; package view derived overdue 1 /
  controls 21 / evidence 1 over the canonical fixture.
- Core byte-identity: SHA-256 of all 8 pre-existing
  `src/grc/*.py` files identical before and after
  (`store.py` still `e2eac653…`, matching the hash recorded
  in tests/README.md for the founding drill).
- **Fresh mutation-verified negative control:** the package
  overdue seam `_package_overdue_count` — in-suite three-leg
  control in `TestPackageDerivationNegativeControl`
  (canonical overdue 1 at 2026-07-01 / 0 on the due date;
  never-count mutant collapses both to 0; mutant-as-expectation
  fails via `assertRaises(AssertionError)`) plus a live drill
  on the real `extensions.py` (the seam's `return count` line —
  line 924, scoped by line number because the same text occurs
  once more as a substring of the summary helper's
  `return counts` — patched to `return 0`) → **161 ran,
  exactly 4 failures**, all in `test_gaps_batch.py`
  (`TestPackages.test_package_view_derives_from_core_records`,
  `TestPackages.test_package_view_tracks_registry_state`, and
  the negative control's canonical + mutant-as-expectation
  arms). Restored from `scratch/extensions.py.premutation`,
  SHA-256 verified identical (`d56ef7b1…`), suite re-ran
  green. Recorded in tests/README.md.
