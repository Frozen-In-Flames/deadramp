# Final GAPS batch — second unit: Remainder Addition — Customer Service L1

Unit: the 1 OPEN entry of the GAPS.md section
**`## Remainder Addition — Customer Service L1 (+1 fork)`**
(the +1 fork is Zendesk / Zendesk Customer Support and Help Desk
Platform, FR1821856903, added to this group by the remainder
census; its spec sheet's ADDENDUM §5 registered this gap). Built
2026-11-08 under `../../gaps-batch/DECISION.md` (the 2026-11-07
ratified triage) and `../../PLATFORM-LAYER.md`. Entry count
verified against both sources before building: GAPS.md's section
lists exactly 1 `- [ ] open` entry and `gaps-batch/inventory.json`
assigns exactly idx 661 to this section — **no discrepancy** with
the brief. Drafted triage: idx 661 `build-extension`.

All extension code is one new module,
`src/custsvc/extensions_addition.py`
(`CustsvcExtensionsAddition`, a second wrapper around the
untouched core store, audit actions prefixed `exta_`); every
existing module — including the first batch unit's
`extensions.py` — is byte-identical (SHA-256 verified against the
pre-build record in `scratch/prebatch-addition-src.sha256`;
`store.py` still `05c749f3…`, first unit's `extensions.py` still
`f4ef5be8…`). No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py` (28 tests; suite **126 →
154**, all passing).

Tier discipline is this group's, kept exactly as the first unit
kept it: writes land on this tier's plain append-only audit log —
no hash chain is called or claimed, no lockout, no auditor role
imported downward from the L3 sibling — and the role matrix is
this group's (admin / agent / viewer; the addition's operational
writes map onto `case_write`, which agents hold and viewers do
not; the summary maps onto `report_read`).

Category doctrine holds on the whole surface: people are named
only by the core's registered opaque requester refs (an
unregistered ref is refused everywhere, so the pinned
identifier-free requester shape governs outreach targets too);
no signature can accept message content — content-shaped
arguments (`message=`, `body=`, `content=`) raise `TypeError`,
pinned by test; and nothing here computes an engagement figure —
views and summaries are counts over this surface's own records,
derived at read, with no float rate, ratio, percentage, or score
representable anywhere (pinned by recursive key/value scan).

## Per-entry disposition

### idx 661 — built (build-extension, as drafted)

> Proactive engagement & outreach: proactive customer engagement and outreach (asserted in substance by the fork's own words, "proactive engagement"; no taxonomy family covers outreach — registered from the described function, not from a claim)

Built in records form, in the shape this group's first batch
unit adjudicated for notification delivery (its entry 6): the
records layer an outreach function runs on is built; the sending
itself is transport and lands as `reference_transport` records,
exactly as notification delivery did. What is built:

- `create_campaign` (`cmp-`): a campaign definition — name,
  `kind` over the three outreach forms the addition addendum
  names in its own words (campaign / nudge / reengagement), a
  channel label and a trigger label held as recorded terms, and
  an optional opaque audience `segment_ref` held as data. The
  stored record's exact key set is pinned; every record carries
  `evaluated_here: False`, `sends_here: False`, and
  `state: definition_only`. A definition is never evaluated: a
  test pins that a campaign whose recorded trigger matches a
  core event creates no attempt and touches no case — attempts
  exist only when an operator records one.
- `record_suppression` (`sup-`): an opt-out record binding a
  registered core requester, by opaque ref, to one campaign's
  scope or to the global scope (`campaign_id` None). Exact
  duplicates are refused. Suppression is this unit's guard: the
  `_is_suppressed` seam derives, over the suppression records,
  whether a requester is suppressed for a campaign.
- `record_outreach_attempt` (`out-`): a record that an outreach
  contact under a campaign was requested of a transport for one
  requester — the campaign must exist, the requester must be a
  registered core requester, and an optional bound case must
  exist in the core. A requester suppressed for the campaign
  (or globally) is **refused whole** at the seam: no record is
  created and no id is consumed (pinned). Every attempt carries
  `reference_transport: True`, `sent_here: False`, and
  `state: recorded_reference_only` — nothing is sent here.
- `record_outreach_report` (`outr-`): one outcome as reported
  by the transport elsewhere, stored verbatim over
  {`reported_delivered`, `reported_failed`, `reported_bounced`,
  `reported_engaged`, `reported_opted_out`}; the report itself
  carries `sent_here: False`. A test pins that a full
  attempt-plus-report flow leaves the bound core case
  byte-identical and every core count unchanged.
- `campaign_view` / `outreach_summary`: derived at read —
  attempt, report, and scoped-suppression counts, report counts
  by outcome, campaigns by kind, and the latest reported
  outcome via the `_latest_outcome` derivation. Counts only;
  nothing is stored on any record.

## Re-judgments (DECISION.md qualification 1)

None. The entry closes with its drafted disposition. The built
closure is bounded as its form states: what is built is the
campaign/suppression/attempt/report records layer; outreach
*sending* is not performed here and every attempt and report
record says so (`reference_transport: True`,
`sent_here: False`), in the first unit's notification form. The
addition fork's by-substance knowledge-base enlargement
(ADDENDUM §5) is not part of this unit — that gap was closed at
this tier by the first batch unit's entry 3, and nothing here
touches it. No catalogue or reputation prose was used to
manufacture any function: the entry rests on the fork's own
words ("proactive engagement"), as recorded in ADDENDUM.md.

## Negative control

Fresh, for this surface: the suppression seam
(`CustsvcExtensionsAddition._is_suppressed`). The canonical
rule: an outreach attempt to a requester suppressed for the
campaign — or globally — is refused whole. The in-suite
three-leg control in `test_gaps_batch_addition.py`
(`TestSuppressionNegativeControl`): the canonical surface
refuses the attempt; the mutant subclass (the seam replaced
with a no-op `return False`) records it; treating the mutant's
outcome as the canonical expectation must fail.

Live mutation drill (2026-11-08, coordinator-verified): the
seam's scoped match block in
`src/custsvc/extensions_addition.py` (the `campaign_id` scope
condition and its `return True`; the block occurs exactly once,
count asserted) was patched in the real file to `return False`.
The full suite ran: **154 tests, exactly 3 failed** —

- `test_gaps_batch_addition.TestOutreachAttempts.test_suppressed_requester_refused_whole`
- `test_gaps_batch_addition.TestOutreachAttempts.test_globally_suppressed_refused_for_any_campaign`
- `test_gaps_batch_addition.TestSuppressionNegativeControl.test_suppression_guard_is_load_bearing`

Mutant output is saved at
`scratch/gaps_batch_addition_mutation_run.txt`.
`extensions_addition.py` was then restored from
`scratch/extensions_addition.py.premutation` and verified
byte-identical (SHA-256 recorded in
`scratch/extensions_addition.py.sha256`) and the suite re-run:
**154 tests, OK**.

Left unresolved: nothing in this unit. HTTP exposure of the
addition surface was out of scope for the batch pattern; the
service layer is untouched.
