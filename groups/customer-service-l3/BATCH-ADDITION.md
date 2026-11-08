# Final GAPS batch — second unit: Remainder Addition — Customer Service L3-adjacent

Unit: the 2 OPEN entries of the GAPS.md section
**`## Remainder Addition — Customer Service L3-adjacent (+1 fork)`**
(the +1 fork is Medallia, Inc. / Medallia GovCloud, FR1711262842,
added to this group by the remainder census; its spec sheet's
ADDENDUM §5 registered these gaps). Built 2026-11-07 under
`../../gaps-batch/DECISION.md` (the 2026-11-07 ratified triage)
and `../../PLATFORM-LAYER.md`. Entry count verified against both
sources before building: GAPS.md's section lists exactly 2
`- [] open` entries and `gaps-batch/inventory.json` assigns
exactly idx 663–664 to this section — **no discrepancy** with the
brief. Drafted triage: idx 663 `build-extension`, idx 664
`stub-engine`.

All extension code is one new module,
`src/custsvc/extensions_addition.py`
(`CustsvcExtensionsAddition`, a second wrapper around the
untouched core store, audit actions prefixed `exta_`); every
existing module — including the first batch unit's
`extensions.py` — is byte-identical (SHA-256 verified against the
pre-build record in `scratch/prebatch-addition-src.sha256`;
`store.py` still `40c4d9c6…`, `audit.py` still `3d096577…`,
first unit's `extensions.py` still `dc1999e6…`). No core
extension was needed. Tests:
`tests/test_gaps_batch_addition.py` (24 tests; suite **168 →
192**, all passing).

The High apparatus binds the addition exactly as it bound the
first unit: writes are fail-closed on the core hash-chained audit
log (a failed audit append rolls back the record and its id
allocation, pinned by test); the separated auditor role is denied
every addition operation, reads included, while its core audit
duty (`verify_chain()` → `(True, None)`, audit query) works
unchanged, pinned by test.

Category doctrine holds on the whole surface: case state (incl.
SLA breach) still derives at read in the core and is untouched
here; survey figures are stored **verbatim** as reported and
never computed, aggregated or ranked (a recorded value is a
report, not a judging engine — no view sums, averages, tallies
or distributes reported values; the only derived numbers are
counts of this surface's own records); report views store no
figures; conversation/message content is never held (respondents
and signals are opaque references only, content-shaped arguments
raise `TypeError`, pinned); AI assistance is **not** part of this
unit — no entry in this section is AI-shaped (the addition fork's
AI claim enlarges the already-registered AI gap, closed at this
tier by the forms recorded elsewhere; this surface contains no
model and no inference-shaped method).

## Per-entry disposition

### idx 663 — built (build-extension, as drafted)

> Survey & feedback-collection engine: survey capture and feedback-signal collection across channels (registered WITH a claim — this fork's satisfaction-surveys claim retires the category's standing named absence at this tier; the records its flagged signals write are Core, the engine is Extended)

Built in records form. The collection engine's honest
in-substrate shape is the records layer its captures report
into: instrument definitions, response records and signal
records. Capture itself — collecting a signal on a channel —
happens in the platform elsewhere, and every record says so
(`collected_here: False`).

- `create_survey_instrument` (`survey-`): an instrument
  definition — name, capture channels held as recorded terms
  over the fork's own channel vocabulary from its claim evidence
  (in_person / survey / call / digital / video / social_media /
  iot), and its response scale as recorded integer bounds
  (booleans/floats rejected, low below high enforced). The stored
  record's exact key set is pinned: no tally, total or
  latest-response key exists on it.
- `record_survey_response` (`sresp-`): one response as reported.
  The respondent must be a requester already registered in the
  core, by opaque `requester_ref`, so the core's pinned
  identifier-free record shape governs them; the channel must be
  one of the instrument's recorded channels; the value must be
  an integer on the instrument's recorded scale (bool/float/
  out-of-scale rejected, no id consumed) and is stored verbatim
  as `reported_value`.
- `record_feedback_signal` (`fsig-`): one feedback signal as
  reported — an opaque `signal_ref` on a named channel,
  optionally bound to the instrument it was collected under, a
  registered core requester, and an existing core case or alert
  (every named binding must exist). Recording a signal writes
  **no** core record: a test pins that responses and signals
  leave the core's case and alert lists byte-identical — the
  records a flagged signal would write remain the core's own
  ingest paths' business, exactly as ADDENDUM.md states.
- `survey_view`: derives at read — response and signal counts,
  response counts per channel, and the latest recorded response
  (id and its verbatim reported value) via the latest-record
  seam below. No reported value is summed, averaged, tallied,
  distributed or ranked anywhere in the view (pinned by key scan
  and by construction).
- `feedback_summary`: counts over this surface's own records
  only (instruments, responses, signals, by channel), derived at
  read, stored nowhere.

### idx 664 — reference (stub-engine, as drafted)

> Platform connectors & integration API surface: connectors into external platforms asserted in substance by the fork's closing bullet (this taxonomy has no integrations family, so no claim fired)

Labeled reference implementation, in the house connector form:

- `register_connector` (`conn-`): a connector definition by
  opaque `connector_ref` (unique on this surface; re-registering
  the same ref is refused), `kind` in {`platform_connector`,
  `api_surface`}, and the external platform's label held verbatim
  as data (the fork names its platforms in its own bullet;
  holding the label asserts no integration with it). Every
  record carries `reference_stub: True` and
  `reference_transport: True`, with `connected_here` /
  `synced_here: False` on its face.
- `record_exchange` (`exch-`): one exchange as reported by the
  platform — direction, outcome verbatim over
  {`reported_completed`, `reported_partial`, `reported_failed`},
  an optional reported record count held as data (a non-negative
  integer; bool/float/negative rejected), and an optional binding
  to an existing core case. `imported_here` / `executed_here:
  False` throughout: nothing was imported, exported or executed
  by this build.
- `connector_view`: derives the exchange count and the latest
  recorded exchange outcome at read via the same latest-record
  seam; the stored connector record carries no count (pinned).

## Re-judgments (DECISION.md qualification 1)

None. Both entries close with their drafted dispositions. The
built closure for idx 663 is bounded as its section states: what
is built is the instrument/response/signal records layer; signal
capture on a channel is not performed here and every record
states it (`collected_here: False`). The founding fork's
third-party catalogue exclusion is not reopened by this unit:
no catalogue prose was used to manufacture any function — both
entries rest on the addition fork's own claims and its own
closing bullet, as recorded in ADDENDUM.md.

## Negative control

Fresh, for this surface: the latest-record seam
(`CustsvcExtensionsAddition._latest_record`). The canonical rule:
a survey view's latest response and a connector view's latest
exchange outcome are the *last* records reported. The in-suite
three-leg control in `test_gaps_batch_addition.py`
(`TestLatestRecordNegativeControl`): canonical views over
two-record histories read the second record on both families;
the mutant subclass (deriving from the first record) reads the
first; treating the mutant's outcomes as the expectations must
fail.

Live mutation drill (2026-11-07, coordinator-verified): the
seam's `return records[-1]` line in
`src/custsvc/extensions_addition.py` (line 227; the line occurs
exactly once, count asserted) was patched in the real file to
`return records[0]`. The full suite ran: **192 tests, exactly 3
failed** —

- `test_gaps_batch_addition.TestSurveyResponses.test_view_counts_and_latest_without_aggregation`
- `test_gaps_batch_addition.TestConnectors.test_exchange_flow_and_view`
- `test_gaps_batch_addition.TestLatestRecordNegativeControl.test_canonical_derives_from_latest_record`

Mutant output is saved at
`scratch/gaps_batch_addition_mutation_run.txt`.
`extensions_addition.py` was then restored from
`scratch/extensions_addition.py.premutation` and verified
byte-identical (SHA-256
`c1f91ac4bfe1ddaabc6c7075f137dbab5d039e6968ec28b2015aece56e87ac00`,
recorded in `scratch/extensions_addition.py.sha256`) and the
suite re-run: **192 tests, OK**.

Left unresolved: nothing in this unit. HTTP exposure of the
addition surface was out of scope for the batch pattern; the
service layer is untouched.
