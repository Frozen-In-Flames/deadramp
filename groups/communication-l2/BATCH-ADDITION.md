# Final GAPS batch — second unit: Remainder Addition — Communication L2

Unit: the 1 OPEN entry of the GAPS.md section
**`## Remainder Addition — Communication L2 (+1 fork)`**
(the +1 fork is Granicus / GovDelivery Communications Cloud,
`F1311252652`, FedRAMP Moderate / Certified, added to this group
by the remainder census; its spec sheet's ADDENDUM §5 registered
this gap). Built 2026-11-08 under `gaps-batch/DECISION.md` (the
2026-11-07 ratified triage) and `PLATFORM-LAYER.md`.

**Entry-count verification (no discrepancy):** GAPS.md's section
lists exactly 1 `- [ ] open` entry, and
`gaps-batch/inventory.json` assigns exactly idx 657 to this
section (drafted **build-extension**). Both sources agree with
the brief's count of 1.

All extension code is one new module,
`src/comm/extensions_addition.py` (`CommExtensionsAddition`, a
second wrapper around the untouched core store, audit actions
prefixed `exta_`); every existing module — the 7 core modules
and the first batch unit's `extensions.py` (`ec801618…`) — is
byte-identical (SHA-256 verified against the pre-build record
in `scratch/prebatch-addition-src.sha256`; `store.py` still
`6ccd412c…`). No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py` (13 tests; suite
**113 → 126**, all passing).

Category doctrines held: communication records hold opaque
references and metadata only — no record shape on the addition
surface can hold message content (signatures accept no
content-shaped parameter; `content=` / `body=` / `subject=` /
`payload=` calls raise `TypeError`, pinned by calls, a
signature scan, and a recursive key scan over every record and
view); sending/transmission never happens (`sent_here` /
`transmitted_here`: False on every record); an audience segment
is never resolved against the directory (no member list,
audience count, or targeted-contact field exists in any shape);
derived values are derived at read and never stored (a
campaign's current reported outcome and its totals of reported
figures — stored records carry no derived key, pinned).

## Per-entry disposition

| idx | Entry (verbatim GAPS.md text) | Drafted | Final | What was built |
|---|---|---|---|---|
| 657 | Marketing automation & citizen-engagement campaign engine: audience targeting / segmentation and automated campaign execution (registered from the fork's described function; its headline "marketing automation platform" phrasing fires no taxonomy family) | build-extension | **reference (re-judged)** | Campaign definition records (`mcam-`, opaque `campaign_ref` unique per surface, verbatim label, declared channel kinds as data, optional core template bound **by id only** — validated through the core store, its subject/body never copied; `reference_stub: True`, `reference_transport: True`, `executed_here` / `targeted_here` / `segmented_here` / `sent_here` / `transmitted_here` / `content_held: False`) + audience segment definition records (`mseg-`, core group ids validated through the core store and opaque criterion refs held **as data** — membership is never resolved, no audience is computed, counted, or listed; `audience_computed: False`) + reported campaign outcome records (`mrep-`, verbatim outcome labels, optional message/delivery counts held exactly as reported with `figures_basis: reported_by_platform`, `measured_here: False`; bools/floats/negatives refused, no id consumed). `campaign_view` derives `current_outcome` (addition seam) and the totals as **sums of the reported counts, stated as such** at read; `segment_view` returns the definition as recorded with the audience unresolved; `addition_campaign_summary` is deterministic record counts only. A full addition flow is pinned to change no core message or delivery record and to dispatch nothing (a bound delivery stays `queued`). |

## Re-judgment — idx 657 (marketing automation): build-extension → reference

Grounds (DECISION.md qualification 1; the brief's category
doctrine, which this unit confirms on close reading): the entry
names an **operated engine** in both of its halves. Audience
targeting / segmentation is a computation over the directory
that selects who receives a campaign; automated campaign
execution composes and sends against that selection. Neither
half is a records function of this substrate, and building
either would be a fake engine: a segment view that resolved
group membership into an audience would be the targeting engine
running, and a campaign surface that composed or dispatched
would be sending, which this category never does (the core's
own dispatch is a labeled reference transport over individually
composed messages, not campaign execution).

What is honestly buildable is the engine's records form, and it
is built in full: campaign and segment **definitions as data**
plus **reported outcomes** — exactly this group's own
adjudicated form for an automation engine (idx 124, workflow /
BPM: definition records copied as data, `executed_here: False`,
closing `reference`), and the sibling Communication L3
addition's form for an operated platform surface (idx 658,
connector definitions + reported exchanges, closing
`reference`). The archiving precedent the brief names (idx 117)
does not carry this entry to `built`: capture records, retention
policies, and legal holds are records the substrate itself
keeps about its own records, whereas a campaign definition is a
definition of work an external engine performs — under this
group's own BATCH.md taxonomy of forms, definitions of external
execution close as labeled reference. Every record therefore
carries `reference_stub: True` and the entry closes as
`reference`, not `built`. The build is identical under either
token; the records surface is the full honest deliverable.

## Negative control (fresh, mutation-verified)

Seam: `_latest_label` in `src/comm/extensions_addition.py` —
the current reported label of an append-only record stream is
its LATEST record's label (used by the campaign view's current
outcome). Live drill on the real file: the seam's return line
(`return records[-1][key]`, the module's only occurrence, count
asserted = 1 before patching) was patched to
`return records[0][key]`; the full suite ran 126 tests with
**exactly 4 failures**, all in
`tests/test_gaps_batch_addition.py` —

- `test_gaps_batch_addition.TestCampaignReference.test_outcome_view_derives_current_and_reported_totals`
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_canonical_view_uses_latest_outcome`
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_seam_directly`
- `test_gaps_batch_addition.TestNegativeControlLatestLabelAddition.test_mutant_earliest_differs` (trips by design: it asserts the literal canonical value against the real implementation)

No core or first-unit test failed. Restored from
`scratch/extensions_addition.py.premutation`, SHA-256 verified
identical (`19df54ae…`), suite re-ran **126, OK**. Recorded in
`tests/README.md`; raw output in
`scratch/gaps_addition_mutation_run.txt`.

## Not covered

Nothing outside the 1 entry of this section. The section's
closing paragraph in GAPS.md (secure transmission explicitly
gaining no claimant; the census-citation verification note)
names no open entry and was not absorbed. The founding Group 11
section's 12 entries were closed by the first batch unit and
were not touched. HTTP exposure of the addition surface is out
of scope for the batch pattern; the service layer is untouched.
PLATFORM-LAYER.md decisions 1–6 are untouched: no identity
provider, no validated cryptography, no retention enforcement,
no session layer, and no hosting or multi-tenancy claim was
built or implied.

Left unresolved: nothing in this unit.
