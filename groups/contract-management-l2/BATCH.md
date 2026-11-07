# Final GAPS batch — Remainder Group 1, Contract Management L2

Date: 2026-11-07. This section of `../../GAPS.md` listed 10
entries; 1 (identity provider / registration verification) was
already closed as `re-scoped` under PLATFORM-LAYER.md decision 1
and is not this unit's. The remaining 9 open entries are closed
by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/contractmgmt/extensions.py`
(`ContractExtensions`, wrapping the core `ContractMgmtStore`;
all seven core modules byte-identical, SHA-256 verified against
the pre-build sums — store.py still `83c2046d…`, the shipped
hash), and `tests/test_gaps_batch.py` (41 tests). Full suite:
**106 → 147 tests**, all passing.

The founding discipline binds every shape built here: this build
is the contract lifecycle system of record. It holds no
regulation text, executes no workflow, runs no auction,
discovers no price, transports nothing, connects to nothing,
and moves no money. Records carry metadata and opaque
caller-supplied references only, plus figures and outcomes
stored exactly as reported by the external systems and people
who actually did the work. That is pinned by exact key-set
assertions per record type, by `TypeError` on any unexpected
keyword argument, and by a recursive banned-key scan over the
extension records, views, and reports. Every "engine" below is
its in-substrate form: records over the group's OWN records
(core records and extension records), plus deterministic
derivations at read.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 1 | Regulatory content & interpretation: FAR / DFARS corpus, agency supplements, updates | built | Clause records (`clz-`; citation + SHA-256 digest + opaque source reference; `content_held_here: False` — the regulation text is never accepted or held, and a smuggled `text=` kwarg raises `TypeError`, pinned) and corpus update records (`cup-`; the updated text's digest, held as data). `clause_view` derives the current digest at read (latest update's digest, else the clause's own); the stored clause carries no current-digest key. Interpretation closes as guidance records (`gui-`): reporter reference, the digest of the guidance text (held elsewhere), optional links to a clause record and/or a core compliance requirement; `interpreted_here: False`, and no guidance text is accepted or held. |
| 2 | Analytics engine: PALT measurement, bottleneck / spend analysis beyond registry counts and sums | built | Deterministic derivations at read over the core records; no new stored records. PALT: for each core award, the exact whole-second span between the recorded opportunity creation and award creation (seam `_palt_seconds` — exact day/second arithmetic over the timestamps' timedelta components, pinned on fixed timestamps); the summary is exact arithmetic over the spans (total, min, max, and a mean rendered as an integer or an exact `"num/den"` fraction string — never rounded). Bottlenecks: counts of the core's own derived flags (open opportunities past close, open protests/data calls overdue, active contracts past period end) plus unawarded submissions and open requirements. Spend: recorded award cents summed by the opportunity kind the records carry, and net modification cents across contracts. `analytics_report` names its method `deterministic_derivation`; a recursive scan pins that no score/rating/ranking key exists anywhere in it. Nothing is estimated. |
| 3 | Opportunity portal front-end (the public / directed web portal itself) | built | Portal definition records (`por-`) and page definition records (`pge-`, optionally bound to a core opportunity) held as data. `rendered_here: False` and `served_here: False` on the records themselves — the definitions are the in-substrate form of the front-end; the browser experience is the embedding deployment's. |
| 4 | Reverse auction engine: live bidding, price discovery | built | Reported bid records (`bid-`; opaque bid reference, the bidding participant's opaque reference — validated against the core participant registry — and the bid amount in integer cents, held as data) and reported outcome records (`auc-`; reported-* labels, a reported winner held as an opaque `reported_winner_ref` verbatim). The opportunity must be a core `reverse_auction` opportunity. Nothing here orders, ranks, or compares bids and no winner or price is derived: `discovered_here: False` and `conducted_here: False` on both shapes, bids list in recording order, and `auction_view`'s key set is pinned to exactly the core view, the bid/outcome records, and their counts. A test pins that recording bids and an outcome leaves the core opportunity view, submissions, and awards byte-identical — any award stays a core award record, made through the core. |
| 5 | Submission intake transport (electronic bid / proposal receipt channel) | built | Intake receipt records (`rcp-`) over core submissions: channel reference and an optional reported SHA-256 digest of what the channel received, held as data. `reference_transport: True`, `transmitted_here: False`, `content_held_here: False` — the records surface is built; the transport itself is the labeled reference, in the Communication line's adjudicated form. The received content is never accepted (a smuggled `content=` kwarg raises `TypeError`, pinned). |
| 6 | Payment processing rails: fee collection / settlement (the core records payments, moves no money) | built | Settlement records (`set-`) over core payment records plus verbatim outcome report records (`srp-`; reported_settled / reported_partial / reported_failed). `settled_here: False` and `moved_here: False` — the core records payments and moves no money, and this surface inherits that exactly. The outstanding settlement total against a payment is capped by the payment's recorded amount via the seam `_check_settlement_bounds` (a settlement whose latest report is `reported_failed` releases its commitment; a partial report leaves the full amount committed, because the report carries no settled figure of its own). Current outcome and the committed/remaining summary derive at read; the stored settlement carries no state key. This entry is the batch's fresh negative control (below). |
| 7 | Communication transport (the secure messaging channel itself) | built | Message transport records (`mtr-`) over core communication records, plus verbatim outcome report records (`mrp-`). `reference_transport: True`, `transmitted_here: False`; the current outcome derives at read and is never stored. The core communication is metadata only, and this surface adds no content field — a smuggled `content=` kwarg raises `TypeError`, pinned. |
| 8 | Workflow execution engine | reference | Labeled reference records, as drafted: run-request records (`wrq-`) against core workflow definitions and reported outcome records (`wrp-`), every record carrying `reference_stub: True` and `executed_here: False`, requests in state `recorded_reference_only`. A test pins that recording a request and a report leaves the core workflow registry byte-identical, and that no callable on the surface has `execute` in its name — the core registry never executes, and neither does this surface. |
| 9 | Integration transport (the system-to-system interfaces themselves) | built (re-judged — see below) | Exchange records (`xch-`) over core integration records: interface, direction, and the record count exactly as the interface reported it, plus verbatim outcome report records (`xrp-`); the current outcome derives at read. `reference_transport: True`, `transmitted_here: False`, `connected_here: False` — the records surface is built; the interface itself is the labeled reference. No exchanged content is accepted (a smuggled `payload=` kwarg raises `TypeError`, pinned). |

Closure tokens: 8 entries close as `built` (regulatory content,
analytics, portal front-end, reverse auction, submission
intake, payment rails, communication transport, integration
transport) and 1 as `reference` (workflow execution).

## Re-judgment — integration transport: stub-engine → built

Grounds (DECISION.md qualification 1; the unit brief's settled
form for all three transport entries): the draft triage is
pattern-based, and on a close reading of this group's spec the
integration entry is the same records form as the two
build-drafted transports in this unit. The core already holds
the interface as a registry record (Core 15); what the gap
names beyond it is the transport — and the in-substrate form of
a transport, per the Communication line's adjudication and the
Energy delivery form, is the receipt/exchange records surface:
records bound to a core record, carrying a figure exactly as
reported (here, a record count) and verbatim reported outcomes,
with `reference_transport: True` on every record and
`transmitted_here` / `connected_here` False. That surface is
genuinely implemented and tested here, and nothing in the entry
requires holding exchanged content (refused by signature) or
connecting to another system. Closing it `reference` would
understate a built records surface for a pattern label.
If the parent judges the draft should stand, the records and
tests are unchanged — only the token differs.

The two build-drafted transports nearest the same line are
stated plainly rather than re-judged:

- **Submission intake (5)** and **communication transport (7)**
  close as `built` in receipt/transport-records form — not as
  channels: the substrate's submissions and communications are
  records, and the records surface over them is the build; the
  channel itself is labeled `reference_transport` on every
  record, exactly as the brief prescribes.

## Negative control

Fresh, for the new code: the settlement bound seam
(`_check_settlement_bounds` in `src/contractmgmt/extensions.py`
— outstanding settlement amounts against a core payment never
exceed the payment's recorded amount). In-suite three-leg
control in `tests/test_gaps_batch.py`
(`TestSettlementBoundsNegativeControl`: the canonical
over-bound cases — one cent over on a single settlement, and
two settlements each within the amount whose sum exceeds it —
raise and store nothing and consume no id; a local mutant gate
waves both through; treating the mutant's outcome as the
expectation fails), plus a live drill on the real file: the
seam's comparison and raise were patched to `return True  #
MUTANT (mutation drill)` (syntax-checked with `compile()`
before the run), and the full suite ran **147 tests with
exactly 2 failures**, both in the batch's own negative-control
tests (`test_single_settlement_one_cent_over_payment`,
`test_two_settlements_each_within_whose_sum_exceeds`) — no core
test failed, and no other batch test failed, because every other
settlement the suite records is within the bound. The file was
restored from `scratch/extensions.py.premutation`, verified
byte-identical by SHA-256 (`scratch/extensions.py.sha256`), and
the suite re-ran green. Recorded in tests/README.md; drill
output in `scratch/gaps_batch_mutation_run.txt`.

## Not covered / honesty notes

- Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the core service layer is
  untouched.
- No record in this unit holds regulation or guidance text,
  bid or proposal content, message content, or exchanged
  content; moves money; executes a workflow; connects to
  another system; or derives a winner, a price, a score, or a
  ranking. The `*_here: False` labels are on the records
  themselves, not only in this document.
- PALT is measured between the timestamps this substrate
  records (opportunity creation → award record). The forks'
  "compress PALT" outcome prose claimed no measurement
  function (UNION-SPEC checked absences); this surface measures
  only what the records state and says so.
- The section's tenth entry (identity provider / registration
  verification service) was already closed `re-scoped` under
  PLATFORM-LAYER.md decision 1 and is untouched by this unit,
  as are the group's platform-layer notes in UNION-SPEC
  (encryption at rest, multi-tenancy, demo identities).
