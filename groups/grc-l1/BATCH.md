# Final GAPS batch — Singleton 43, Governance, Risk, and Compliance (GRC) L1

Unit: GAPS.md section **"Singleton 43 — GRC L1 (1 fork)"**, the
section's 4 OPEN entries (inventory idx 415–418), worked per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). One new
module, `src/grc/extensions.py` (`GrcExtensions` wrapping the
core `GrcStore`), plus `tests/test_gaps_batch.py`. **All
pre-existing core modules are byte-identical** (SHA-256 checked
before/after against `scratch/prebuild-src.sha256`, drill
included; `store.py` still `e2eac653…`, the hash recorded in
tests/README.md for the founding drill); no service routes were
added — the batch surface is store-level, following the sibling
batch units' pattern. Suite: **118 → 142 tests, all passing.**

The category doctrine binds every disposition below: **no
computed score, rating, grade, or percentage anywhere**.
Posture in this group is counts only, enforced by recursive key
scans; the extension surface is scanned the same way
(`TestExtensionInvariants`). One spelling consequence, stated
plainly (the same one the sibling GRC L2 unit recorded): the
founding scan forbids any key containing `score`, so the
boundary the batch brief spells `scored_here` is carried on
this group's records as `computed_here: False` — the same
statement (no value was computed here), in the only key form
this group's pinned invariant allows. Reported statuses,
outcomes, and values are recorded **verbatim**, never computed;
anything date-based or "latest"-shaped is derived at read,
never stored. Extension mutations write to the core's
append-only audit log under `ext_` action names; denied
attempts raise and change nothing (auditing a denial at this
store-level surface is the HTTP layer's responsibility, exactly
as in the core — there are no extension HTTP routes).

**Tier discipline.** This group sits at Low / L1: the core's
plain append-only audit and three-role matrix are used
unchanged. No hash chain, no lockout, and no auditor role were
imported downward from the Moderate/High sibling tiers, and the
extension asserts no baseline beyond the group's own spec.

## Per-entry dispositions

**Built (1):**

- **Trust Center publication (customer-facing publication of
  the security program description / posture; core posture is
  internal counts)** (idx 416) — *built in
  publication-records form, as drafted.* Publication records
  store **no figures at all** (exact key set pinned by test:
  id, system, title, note, and the two boundary labels
  `published_here: False` / `exported_here: False`).
  Release records hold a reported publication event (label
  verbatim — a version or channel label) against a
  publication. The publication *view* is derived at read from
  the core's records — the system's name, the core's own
  counts-only posture summary unmodified, the release count,
  and the latest release label — so the view tracks registry
  state (records added after the publication was registered
  appear in its next view, test-pinned) while the stored
  record never gains a figure. No page is rendered, published,
  or exported; presenting the view on a customer-facing
  surface is the embedding organization's step, stated on the
  record. The form mirrors the sibling GRC L2 unit's
  authorization-package records (idx 359, shipped): the
  records function a substrate genuinely performs — register
  the publication, derive what it would show from the
  registry — is built and tested; the external act the entry
  names (customer-facing presentation) is not claimed.

**Reference (3, labeled reference implementations, as drafted):**

- **Questionnaire automation engine (a named activity in the
  fork's prose that no taxonomy family names)** (idx 415) —
  questionnaire definition records holding the questions
  **as data** (`reference_stub: True`,
  `administered_here: False`, `reuse_applied_here: False`)
  and response records holding a respondent's answers
  verbatim as data, exactly as reported, with the response
  status verbatim. The view derives response counts (total
  and per verbatim status) and the latest reported status at
  read. Test-pinned boundaries: nothing is administered or
  sent, and no prior answer is ever copied into a response
  by this build — the answer-reuse automation the entry
  names is the external engine's, and a response here is a
  record of a report, not an act of this build.
- **Vendor risk assessment engine (evaluating / scoring
  vendors — the risk claim's engine remainder; the records
  are Core and no score is computed)** (idx 417) — shipped
  in the category's adjudicated reported-value records form
  (sibling GRC L2 idx 357, GRC L3-adjacent idx 419/421, GRC
  untiered scoring surface): assessment-rule records hold a
  rule's text verbatim as data (`reference_stub: True`,
  `method: recorded_rules_only`, `applied_here: False` — a
  rule is never applied to any record by this build, pinned
  by test: recording an assessment leaves the rule record
  byte-identical), and vendor-assessment records hold an
  assessor's reported `outcome` and optional reported value
  **verbatim as labels** against a governed system (vendors
  are governed-system records in this substrate), carrying
  `evaluated_here: False` and `computed_here: False`. The
  summary aggregates counts of the recorded labels only.
  Test-pinned: a vendor assessment creates **no** core
  finding and leaves the core posture unchanged. The
  evaluating/scoring computation the entry names is the
  engine's and stays absent — that is what makes this a
  labeled reference implementation at its drafted token,
  rather than the `built` token the L2 scoring entry took:
  there, the entry's own parenthetical bounded the records
  half as the core's and the disposition could rest on them;
  here the entry names the *assessment engine itself* as
  this fork's excess (its records half is already Core per
  the entry's own text), so the honest closure is the
  reference form with the records substance built inside it.
  If the parent prefers the `built` token, only the token
  changes — the code is identical either way.
- **Continuous-monitoring engine & evidence-collection
  integrations (automated control checks and evidence
  collection from connected systems; overlaps Group 33's
  registered validation-engine and feed entries, named here
  from this fork's own claims)** (idx 418) —
  collection-source records (definitions of API / telemetry
  sources, `reference_stub: True`,
  `reference_transport: True`, `connected_here: False`,
  `collected_here: False`), monitoring-observation records —
  the monitoring **intake**: an external engine's reported
  observation, status verbatim, optionally against a catalog
  control validated against the group's own registry
  (`monitored_here: False`) — and collection-run records
  holding a collector's reported status and reported artifact
  count (booleans, floats, and negatives rejected at the
  boundary). The source view derives observation/run counts,
  per-status counts, the latest reported observation status,
  and the summed *reported* artifact count at read, stated as
  a sum of reports. Test-pinned boundaries, per the
  UNION-SPEC's own ruling ("Recording the result is Core;
  performing the validation is Extended"): an observation
  creates **no** core indicator result and a collection run
  creates **no** core evidence record — core results and
  artifacts land through the core's own operations, by a
  person. No automated control check runs here and nothing
  is collected from any connected system.

## Re-judgments

None at the disposition level: all 4 entries landed at their
drafted triage tokens (1 build-extension, 3 stub-engine). Two
form-level calls were made on close reading and are recorded
per entry above, following DECISION.md qualification 1's
instruction to ground the form in the owning group's spec:

1. **idx 416** closes `built` in publication-records form on
   the sibling GRC L2 package-records precedent (idx 359):
   the buildable half of the entry is the registry record and
   its derived view; the customer-facing presentation half is
   the embedding organization's step and is stated absent on
   every record (`published_here: False`).
2. **idx 417** keeps its drafted `reference` token with the
   adjudicated reported-value records built inside the
   labeled reference form, on the grounds stated per entry —
   the distinction from the L2 scoring entry's `built` token
   is the two entries' own texts, not a change of doctrine:
   the computation stays absent under either token.

## Long tail — named, not covered by this unit

- The section's platform-layer sentence (encryption at rest,
  TLS when configured, multi-tenancy, IA-2 demo-identity
  hooks) stands closed in writing under PLATFORM-LAYER.md
  before this unit; untouched here.
- `policy_management` is a **named absence** in this group's
  spec (no policy vocabulary in the fork's prose; the same
  absence as at L2) — not a gap, not built, unchanged.
- Group 33's registered extended families (automated evidence
  validation, posture/risk scoring engines, workflow
  automation engines, vulnerability scanning engine,
  automated KSI validation, FedRAMP authorization package
  generation, hosted enclave & PaaS operations) are registered
  under Group 33 and were worked by that group's own batch
  units; they are not re-registered or absorbed here. Where
  this unit's idx 418 overlaps Group 33's validation-engine
  and feed entries, the overlap is the one the section's own
  text names; this unit's surface is this fork's remainder,
  in this group's substrate.
- No HTTP routes were added for the extension surface; HTTP
  exposure was out of scope for the batch pattern (extensions
  land in `src/` with tests), and the service layer is
  untouched.

## Verification (coordinator's own run)

- Full suite **142/142 OK** on the coordinator's run (118
  before), plus a live end-to-end smoke exercising all four
  entries' surfaces: questionnaire view derived 1 response /
  latest `submitted`; publication view tracked a core finding
  added after registration (findings 1, overdue 1 at
  2026-07-01) while the stored record kept its exact 8 keys;
  vendor summary counted the verbatim labels; source view
  summed the reported artifact count; core indicator results
  and evidence stayed empty across the monitoring intake.
- Core byte-identity: SHA-256 of all 8 pre-existing
  `src/grc/*.py` files identical before and after
  (`store.py` still `e2eac653…`, matching the hash recorded
  in tests/README.md for the founding drill), verified with
  `sha256sum -c` after the mutation drill restore.
- **Fresh mutation-verified negative control:** the
  latest-label seam `_latest_label` — in-suite three-leg
  control in `TestLatestLabelNegativeControl` (canonical
  latest is the most recent record / earliest-reading mutant
  subclass misstates it / mutant-as-expectation fails via
  `assertRaises(AssertionError)`) plus a live drill on the
  real `extensions.py` (the seam's
  `return records[-1][key] if records else None` line —
  occurrence count asserted 1 before patching — replaced
  with `records[0]`) → **142 ran, exactly 4 failures**, all
  in `test_gaps_batch.py`
  (`TestQuestionnairesReference.test_response_verbatim_and_view_derives`,
  `TestPublicationsBuilt.test_releases_verbatim_and_view_derives_latest`,
  `TestMonitoringReference.test_source_view_derives_counts_and_latest`,
  and the negative control's canonical arm). Restored from
  `scratch/extensions.py.premutation`, SHA-256 verified
  identical (`99838d1b…`), suite re-ran green. Recorded in
  tests/README.md.
