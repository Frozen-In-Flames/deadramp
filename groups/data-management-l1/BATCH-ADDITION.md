# Final GAPS batch — second unit: Remainder Addition — Data Management L1

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Data Management L1 (+1 fork)`**
(the +1 fork is DevResults, FR2100845343, added to this group by
the remainder census; its spec sheet's ADDENDUM §5 registered
these gaps). Dispositions follow
`../../gaps-batch/DECISION.md`; platform-layer closures follow
`../../PLATFORM-LAYER.md`.

**Entry-count verification:** GAPS.md's section lists exactly 2
`- [ ] open` entries, and `gaps-batch/inventory.json` assigns
exactly idx 665 and 666 to this section — both drafted
`build-extension`. The brief's count of 2 open entries is
confirmed; **no discrepancy**. This unit built and closes those
2 entries.

Everything landed as ONE new module,
`src/datamgmt/extensions_addition.py`
(`DataMgmtExtensionsAddition`, wrapping the core
`DataMgmtStore`), with audit actions prefixed `exta_`. All 8
pre-existing `src/datamgmt/` modules — the 7 inherited core
modules and the first batch unit's `extensions.py` — are
byte-identical (SHA-256 verified against the pre-build record in
`scratch/prebatch-addition-src.sha256`; `store.py` still
`dc35677c…`, the first unit's `extensions.py` still
`092befdc…`). No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py` (33 tests). Suite:
**239 → 272**, all passing, including this unit's fresh
mutation-verified negative control recorded in
`tests/README.md`.

Tier discipline holds: this is the Low / FAR 52.204-21 build.
The extension enforces through this group's own three-role
matrix (admin / steward / viewer) over the plain append-only
audit log — no hash chain, no lockout, no auditor role was
imported from the Moderate/High siblings, and none exists here.

The group's honesty posture carries into this unit unchanged:
the enlarged group holds **zero claims across both forks**
(`ADDENDUM.md` §2–§4), so these surfaces are the
census-registered gaps of the addition fork's *described*
functions — the records layer those functions' operation
presupposes, built over the substrate's own records — not
functions either fork was found to claim. Cross-cutting, per the
substrate's hard privacy rule: **no record shape in the new
module can hold dataset content, a response value, or a record
payload** — frameworks, indicators, instruments, and fields are
definitions and labels; reports and runs hold outcomes and
figures **verbatim as reported** plus bindings to core records;
every derived value (summary counts, outcome tallies, latest
reported outcome/value, the reported-record total) is computed
at read and never stored. A recursive scan over every record
and view the surface produces pins the absence of
content-shaped keys, and a surface pin asserts no collection,
submission, rendering, measurement, or execution method exists
on the class.

## Per-entry disposition

### idx 665 — built (build-extension, as drafted)

> M&E / results-management platform functions: indicator and results frameworks, progress measurement (a domain application asserted across the fork's description; no taxonomy family covers it)

Built in records form. The records half of an M&E platform —
frameworks, indicators, and the progress record — lands over
the core's own records; the measurement half is a domain
application over programme data this substrate does not hold,
and is stated absent on every record (`measured_here: False`):

- `define_results_framework` (`rfw-`): a framework definition —
  name, opaque `program_ref`, optional binding to a core
  dataset (an unknown dataset is refused, no id consumed).
  The stored record's key set is pinned: it carries no count,
  total, or status.
- `register_indicator` (`ind-`): an indicator definition under
  a framework — name (unique per framework), unit held as a
  label, and optional `baseline_reported` / `target_reported`
  figures recorded as the framework's declared terms, held
  verbatim as declared (bool figures refused at the boundary).
  Nothing is measured against them here.
- `record_progress_report` (`prg-`): a progress report binding
  an indicator to exactly one core ingestion record — the
  substrate's own record of the data the report rests on. When
  the framework names a dataset, a cross-dataset ingestion is
  refused; one ingestion backs at most one report per
  indicator. `outcome` (over `reported_progressing` /
  `reported_on_track` / `reported_off_track` /
  `reported_no_data`) and the optional `value_reported` are
  stored **verbatim as reported** — `measured_here: False`,
  `computed_here: False`.
- `results_summary`: derives indicator and report counts,
  per-outcome tallies, and the latest reported outcome and
  value (read through the `_latest_progress_report` seam — this
  unit's negative control) at read, joined with the core
  provenance total over completed ingestions of the framework's
  dataset (`None` when the framework names no dataset).

### idx 666 — built (build-extension, as drafted)

> Data-capture tooling & collection instruments: capture tooling and instrument design (distinct from the web-capture engine already registered under this group's founding fork and from the guided-interview engine)

Built in records form, in the entry's own named scope —
*tooling and instrument design*: the design layer is
definitions, and that is what lands. The fielding half
(rendering an instrument, distributing it, collecting responses
with it) happens at the point of origin, outside this build,
and is stated absent on every record (`collected_here: False`,
`content_held: False`):

- `define_collection_instrument` (`cin-`): an instrument
  definition — name, `kind` over {`survey_form`, `field_form`,
  `interview_guide`, `observation_checklist`, `mobile_form`,
  `paper_form`, `other`}, optional version label.
- `add_instrument_field` (`cif-`): a field definition —
  `field_name` (unique per instrument) and `field_kind` over
  {`text`, `number`, `date`, `choice`, `boolean`, `free_text`},
  plus a `required` flag held as a declared term of the
  definition. The field record's key set is pinned: a field
  definition is a shape an instrument declares, and it has no
  value slot — no response can be recorded against it here.
- `record_capture_run` (`crn-`): a capture run binding an
  instrument to exactly one core ingestion record; the run
  takes its dataset and source **from that core record**, never
  from the caller. `outcome` (over `reported_completed` /
  `reported_partial` / `reported_failed`) and the optional
  `records_reported` are the instrument's own report, stored
  verbatim as reported.
- `instrument_summary`: derives field and run counts and
  per-outcome tallies at read; `total_records_reported` is the
  sum of the runs' own reported counts, stated on the view as a
  total of reports, with count-less runs tallied separately as
  `runs_without_reported_count`.

The two distinctions the entry's own text draws are preserved:
this surface is not the founding fork's web crawling & snapshot
capture engine (the first unit's crawl targets and captures,
over web archives — untouched), and it is not the category's
guided-interview engine (an interview-execution stub at the
sibling tiers): instruments here are general-purpose programme
data-capture definitions, per ADDENDUM §5.

## Re-judgments

None. The drafted split held on close reading against this
group's spec and addendum: both entries carry in records form
(2 built, 0 reference). Expected closure arithmetic for the
parent: **2 entries closed — 2 built, 0 reference, no token
overrides.**

The nearest-the-line call is recorded plainly: idx 665's entry
text names "progress measurement" as part of the platform's
function. What is built is the results *record* — frameworks,
indicator definitions, and progress reports whose figures are
reported, never measured — with `measured_here: False` on every
record and view; the substrate presupposition is the same one
ADDENDUM §3 records for the fork (partner results held as
registered datasets, arrivals recorded as ingestions). A
surface that computed progress from data it does not hold would
be a fake engine; this one states, on its face, that progress
was reported to it. The same reasoning covers idx 666's
fielding half, above.

## Named as NOT covered by this unit

- **The section's two substance memberships** — query &
  visualization engines and the integration runtime & connector
  engine gaining this fork by substance (GAPS.md prose under
  this section; ADDENDUM §5). They are not among this section's
  entries: both families are registered under the category
  union's own sections (Groups 12 and 28), were closed by those
  units, and are not re-registered or re-closed here.
- **Project management & team collaboration** — asserted in the
  fork's first sentence, booked nowhere in this group by the
  addendum's deliberate decision (Operations and Collaboration
  functions). Not absorbed.
- **The founding section's 5 entries** (Singleton 38 — web
  crawling, rendering, change detection, archive sealing &
  replay, full-content search) — closed by this group's first
  batch unit in `extensions.py`; untouched, byte-identical.
- **Measurement and collection themselves** — the domain
  application that computes progress over programme data, and
  the instruments as fielded tools that gather responses. This
  unit builds their records layer only, and every record
  carries that bound on its face.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
