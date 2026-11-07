# Final GAPS batch — Remainder Singleton 63, Research L1

Date: 2026-11-07. This singleton's section of `../../GAPS.md`
listed 11 open entries (inventory idx 714–724); all 11 are
closed by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/research/extensions.py`
(`ResearchExtensions`, wrapping the core `ResearchStore`; all
seven core modules byte-identical, SHA-256 verified against the
pre-build baseline — store.py still `ff43a9ac…`), and
`tests/test_gaps_batch.py` (46 tests). Full suite: **96 → 142
tests**, all passing.

The founding privacy discipline binds every shape built here,
pointedly for this fork: studies are opaque caller-supplied
references only. No record shape holds a study's title or
abstract text, a protocol's prose, an extracted value, a study
result, or a score — pinned by exact key-set assertions per
record type, by a recursive forbidden-key scan over every
extension record and view, and by `TypeError` on any unexpected
keyword argument (a `study_title=`, `text=`, or `value=`
argument can never enter a shape).

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 714 | Systematic review automation engine (living systematic reviews) | reference | Automation reference records (`aut-`; `reference_stub: True`, state `recorded_reference_only`, `automation_active_here: False`, `reviews_updated_here: False`) + living-update event records (`aue-`) recorded as reported (`applied_here: False`). Nothing runs, nothing is kept "living" here; an event is a landing form for something that happened elsewhere, if it happened. |
| 715 | Literature search-strategy execution | reference | Strategy reference records (`sst-`) holding an opaque QUERY REFERENCE and source references as data — the strategy text lives elsewhere (`strategy_text_held_here: False`), `executed_here: False` — + execution reference records (`sex-`) holding a run label and a result COUNT as reported (`searched_here: False`). Nothing is searched here. |
| 716 | Title/abstract & full-text screening pipeline | built | Screening records (`scr-`) binding an opaque study ref to a stage (`title_abstract` / `full_text`), a protocol version, and a reviewer decision recorded VERBATIM from the reported-* vocabulary; `screened_by_engine: False`. The pipeline moves nothing automatically: stages are independent records (a full-text record needs no title/abstract record — pinned by test), one decision per (study, stage, reviewer), duplicates refused whole. Screening binds to the CURRENT protocol version through the currency seam; screening against a superseded version is refused. `screening_summary` derives counts by stage/label at read. |
| 717 | Data extraction from studies | built | Extraction form definitions (`exf-`): field REFERENCES held as data, duplicates refused; `field_count` derived at read in the form view, never stored. Extraction records (`exr-`) carry a study ref, a subset of the form's field refs (unknown refs refused whole), a recorded state label, and an opaque extractor ref — `values_held_here: False` on both shapes; no parameter of any method can accept an extracted value (a `value=` keyword raises `TypeError`). Nothing is extracted from any text here. |
| 718 | Quality assessment & regulator verification support | reference | Criteria set records (`qac-`; criterion references as data, `assessed_here: False`), outcome records (`qao-`; an assessor's label verbatim from the reported-* vocabulary, `assessed_here`/`verified_here: False`), and verification records (`qav-`; a regulator/sponsor verifier's label as reported, `verified_here: False`) — all `reference_stub: True`, state `recorded_reference_only`. The substrate is the records form a quality process's outcomes land in, which is the support the entry names; nothing is assessed or verified here. `quality_summary` derives counts of recorded labels. |
| 719 | Review protocol creation | built | Protocol records (`pro-`) holding criterion REFERENCES as data (`protocol_text_held_here: False` — the protocol's prose is never held). Versions are append-only records under one reference; currency is DERIVED at read through the single seam `_current_protocol_record` (highest version) and never stored — the stored record carries no `is_latest`/`latest_version` key (pinned). `protocol_view` / `current_protocol` expose the derivation; `revise_protocol` appends version n+1 leaving prior versions untouched. |
| 720 | Meta-analysis export | built | Export manifest records (`exp-`) carrying `reference_transport: True`, `exported_here: False`, `statistics_computed_here: False`. The manifest view derives counts over the program's held screening/extraction records at read (screening records, distinct studies, studies with a full-text `reported_include`, extraction records, fields addressed; `method: deterministic_counts`). The stored manifest carries no count keys. Nothing leaves this substrate and no meta-analytic statistic is computed anywhere. |
| 721 | Shared dictionary management | built | Dictionary records (`dic-`) + term records (`trm-`) holding an opaque DEFINITION REFERENCE per term (`definition_text_held_here: False` — definition text lives elsewhere). Revisions are append-only under one term ref; the current revision is derived at read (`term_view`'s `latest_revision`/`is_latest`, never stored); `list_terms(current_only=True)` resolves each family through the same derivation. |
| 722 | Project / team / role administration for review programs ("management of projects, teams, roles" is the noun in its text, not the verb the taxonomy's family wants) | built | Review program records (`prg-`; ref unique per commons) + membership records (`pmb-`) binding an OPAQUE member reference to a role label recorded verbatim — duplicate (member, role) pairs refused; no identity data exists in either shape (a member takes no name/email/identifier field; an `email=` keyword raises `TypeError`). `program_summary` derives member/role/protocol counts at read. |
| 723 | Customizable review workflows | reference | Workflow definition records (`wfd-`) holding step references as data + run records (`wfr-`) holding a label as reported — every record `reference_stub: True`, state `recorded_reference_only`, `executed_here: False`. Definitions are never executed here (pinned: recording a run leaves the definition record byte-identical), mirroring the substrate rule that registries hold definitions only. |
| 724 | Human-in-the-loop AI suggestion surface | built | Suggestion records (`sug-`) holding a label recorded as reported from the suggest-* vocabulary plus its source label; `generated_here: False` — nothing is generated here and no generated text can be supplied (a `generated_text=` keyword raises `TypeError`). Human decision records (`hdc-`) hold a decider's label verbatim (action: `decide`). The human-in-the-loop property is structural and pinned by test: recording a suggestion and a human decision leaves the screening record it concerns BYTE-IDENTICAL (internal record and public view compared before/after). Current decision state is derived at read through `_current_decision_label` (latest label, else `undecided`) and never stored on the suggestion record. |

Closure tokens: 7 entries close as `built` (716, 717, 719,
720, 721, 722, 724) and 4 as `reference` (714, 715, 718, 723).

## Re-judgments

None. Every build-extension entry was carried in the records
form described above under the founding no-content discipline,
and every stub-engine entry shipped as its drafted labeled
reference implementation. The two entries nearest the line are
stated plainly rather than re-judged:

- **Meta-analysis export (720)** is built as a manifest record,
  not an export: the manifest's view derives counts over records
  this substrate already holds, and the record itself states
  `exported_here: False`. Producing an export file — let alone
  computing a meta-analysis — would require study data this
  substrate structurally cannot hold, so the records form is the
  only honest build form, and it is what the entry's disposition
  (build-extension) lands as.
- **Quality assessment & verification (718)** stays a stub, as
  drafted: assessment criteria are held as data and outcomes are
  recorded as reported, but no assessment or verification is
  performed here — performing one is exactly the engine the
  stub-engine disposition names as external.

## Negative control

Fresh, for the new code: the protocol currency derivation
(`ResearchExtensions._current_protocol_record` — highest
version wins). In-suite three-leg control in
`tests/test_gaps_batch.py`
(`TestProtocolCurrencyNegativeControl`, mutant subclass reads
the earliest version), plus a live drill on the real file: the
seam was patched to `return versions[0]`, the full suite ran
**142 tests with exactly 6 non-passing** (4 failures + 2 errors,
all in `test_gaps_batch.py`, the currency-derivation-dependent
set: the two protocol currency tests, the two screening-binding
tests, and the control's two canonical arms — the
mutant-agreement tests pass under both by construction), then
the file was restored from
`scratch/extensions.py.premutation` and verified SHA-256
identical (`9d1c6634…`); suite green again. Full record in
`tests/README.md`; drill list in
`scratch/gaps_drill_failures.txt`.

## Core integrity

No core module was modified: `src/research/*.py` SHA-256 sums
match the pre-build baseline exactly (store.py `ff43a9ac…`).
The extension is store-level only (no HTTP routes), matching
the sibling batch units' pattern — the core `service.py` is
byte-identical and untouched.
