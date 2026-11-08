# Final GAPS batch — second unit: Remainder Addition — GRC L3-adjacent

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — GRC L3-adjacent (+1 fork)`** (the +1
fork is Exiger Federal Cloud (EFC) - High, FR2122140784A, added
to this group by the remainder census; its spec sheet's
ADDENDUM §5 registered these gaps). Dispositions follow
`../../gaps-batch/DECISION.md`; platform-layer closures follow
`../../PLATFORM-LAYER.md`.

**Entry-count verification:** the brief's count is confirmed,
no discrepancy — GAPS.md's section lists exactly 2 `- [] open`
entries, and `gaps-batch/inventory.json` assigns exactly
idx 670–671 to this section, both drafted `build-extension`.
This unit built and closes those 2 entries.

Everything landed as ONE new module,
`src/grc/extensions_addition.py` (`GrcExtensionsAddition`,
wrapping the core `GrcStore`), with audit actions prefixed
`exta_`. All 9 pre-existing modules — the 8 founding core
modules and the first batch unit's `extensions.py` — are
byte-identical (SHA-256 verified against the pre-build record
in `scratch/prebatch-addition-src.sha256`, drill included;
`store.py` still `0fe88eb1…`, first unit's `extensions.py`
still `5b2d7da2…`). No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py`. Suite: **207 → 228**, all
passing.

The category doctrine binds every disposition below: **no
computed score, rating, grade, or percentage anywhere**.
Posture in this group is counts only, enforced by recursive key
scans; the addition surface is scanned the same way
(`TestAdditionInvariants`). Reported outcomes and values are
recorded **verbatim**, never computed; anything date-based or
"latest"-shaped is derived at read, never stored. The High
apparatus binds the addition exactly as it bound the first
unit: writes are fail-closed on the core hash-chained audit log
(a failed audit append rolls back the record and its id
allocation, pinned by test); the separated auditor role is
denied every addition operation, reads included, while its core
audit duty (trail read, `verify_chain()` → `(True, None)`)
works unchanged, pinned by test. The Trust Center ruling from
the GRC L1 unit is carried to this surface and pinned: recording
on it creates **no** Core indicator result, evidence, or finding
— the Core's posture summary is byte-identical before and after
a full addition flow.

## Per-entry dispositions

**Built (2, both as drafted, in records form):**

- **Third-party risk & due-diligence intelligence platform:
  third-party due diligence and third-party management
  intelligence (registered from the fork's described function;
  its entire description is one 243-character sentence naming
  its product and four of its own modules, and the word "risk"
  appears nowhere in it)** (idx 670) — *built in records form,
  not re-judged.* The entry's substance is the fork's Due
  Diligence Intelligence (DDIQ) and Third Party Management
  (3PM) modules: a research/intelligence engine over vendors
  and counterparties. The records surface that work presupposes
  is built: third-party registrations (`register_third_party`,
  `tpa-`) keyed by unique opaque caller-supplied references,
  optionally bound to a governed system, holding a recorded
  review due date whose review status is **derived at read,
  never stored** (`derive_third_party_review_status` — this
  unit's fresh negative control targets that derivation); and
  due-diligence records (`record_diligence`, `ddq-`) holding
  the diligence kind and the reported outcome **verbatim**,
  optionally linked to the Core evidence record the diligence
  produced (validated to exist; this surface files nothing
  itself — the ADDENDUM's own note that the findings such work
  produces are ingestible by the Core today is the boundary:
  they land in the Core only through the Core's own
  operations). Every record carries `researched_here: False`:
  no research or investigation is performed here, and no
  third-party standing is computed — an outcome is a label the
  diligence reported, stored exactly as reported. Grounds for
  keeping the drafted `built` token are the founding unit's
  own (BATCH.md, idx 419/421): where an engine's output is
  label-shaped, the records surface that holds it verbatim —
  with referential validation, fail-closed writes, and
  counts-only aggregation — is genuine substrate work, not a
  labeled placeholder; a reference stub would understate it,
  and a build that *performed* the diligence would misstate
  it. The per-third-party view (`third_party_view`) derives
  the diligence count, the latest recorded outcome, and the
  observation count at read, test-pinned to track registry
  state while the stored record never gains a figure.
- **Supply-chain risk visibility & analytics platform: supply
  dynamics and supply-chain visibility analytics (registered
  from the described function; bare "Analytics" is not the
  posture-reporting family and, per category doctrine, no
  score follows from it)** (idx 671) — *built in records form,
  not re-judged.* The entry's substance is the fork's Supply
  Dynamics (SDX) and Analytics modules: a visibility/analytics
  engine over supply chains. The records surface is supply
  observation records (`record_supply_observation`, `sco-`)
  against a **registered** third party (an unknown third party
  or governed system is refused whole, no id consumed): a
  dimension label and a reported value, both verbatim — the
  reported value is held as the label it was reported as,
  never parsed, summed, or rolled up, carrying
  `measured_here: False` and `computed_here: False`. The
  "analytics" half lands as `addition_summary`: counts of
  this surface's own recorded records only — third parties by
  derived review status at the as-of date, diligence records
  by verbatim kind and outcome, observations by verbatim
  dimension — derived at read in the Core's counts-only
  posture discipline. That is the whole of the analytics this
  substrate performs, and the entry's own registration is the
  bound: it names the ADDENDUM's ruling that any scoring or
  prediction machinery belongs to this gap's engine side and
  to the AI risk-prediction gap, never to a records surface;
  no score is computed here, and the recursive key scan pins
  that no score-shaped key exists anywhere on the surface.
  Distinct from the first unit's supply-chain *event* records
  (idx 427, the founding fork's Illuminate ecosystem):
  those are event records against governed systems and opaque
  counterparties; these are reported observations about a
  registered third party's supply chain, with the registry
  binding as the referential discipline — the two surfaces
  record different things and neither duplicates the other.

## Re-judgments

None. Both entries landed at their drafted `build-extension`
tokens, in the records form above. The call was considered per
entry under qualification 1 of DECISION.md, on the founding
unit's shipped reasoning: both entries' buildable halves are
label-shaped records (a reported diligence outcome; a reported
observation value) that a records substrate holds verbatim
without pretending to the computation behind them — the same
shape the L3 founding unit closed as built for the prediction
entries (idx 419/421) and the sibling GRC L2 addition closed as
built for its lifecycle/report records. Had either entry
required computing a value — a third-party risk rating, a
supply-chain risk score, an aggregated analytic over reported
values — it would have been re-judged to `reference` on
doctrine grounds; neither does, and the surfaces are pinned so
no such value can be produced from them.

## Long tail — named, not covered by this unit

- The **Singleton 44 founding section's** 12 entries were the
  first batch unit in this directory (`BATCH.md`, shipped);
  untouched here, and this unit's module does not modify that
  unit's code or tests.
- The **AI risk prediction engine** gap (founding section)
  gained the Exiger fork by substance at census time, booked
  once there; this unit does not re-book it, and nothing here
  is prediction machinery.
- `policy_management` remains a **named absence** at this tier
  (0 of 2, per the ADDENDUM); nothing in this unit changes
  that.
- The High baseline platform-layer gaps (IA-2(1)/(2)/IA-5,
  SC-13, SC-28, AU-11, AC-11/AC-12) stand on PLATFORM-LAYER.md,
  not on this unit.

## Verification (coordinator's own run)

- Full suite **228/228 OK** on the coordinator's run (207
  before), plus a live in-process smoke: registration →
  evidence-linked diligence record → supply observation →
  derived view (`review_overdue` at an as-of past the due date,
  latest outcome, counts) → counts-only summary → audit chain
  `(True, None)`.
- Core byte-identity: SHA-256 of all 9 pre-existing
  `src/grc/*.py` files identical before and after
  (`scratch/prebatch-addition-src.sha256`).
- **Fresh mutation-verified negative control:** the return line
  of `_third_party_review_is_overdue` in the real
  `extensions_addition.py` patched from `return as_of_date >
  due` to `return False` (occurrence count asserted = 1) →
  **228 ran, exactly 5 failures**, all in
  `test_gaps_batch_addition.py` (the derived-status canonical,
  the summary's status buckets, the third-party view, and the
  negative control's canonical + end-to-end arms). Restored
  from `scratch/extensions_addition.py.premutation`, SHA-256
  verified identical (`scratch/extensions_addition.py.sha256`),
  suite re-ran green. Recorded in tests/README.md.
