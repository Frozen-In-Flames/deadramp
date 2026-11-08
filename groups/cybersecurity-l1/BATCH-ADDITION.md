# Final GAPS batch — second unit: Remainder Addition — Cybersecurity & Risk Management L1

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Cybersecurity L1 (+1 fork)`**
(the +1 fork is HackerOne / HackerOne Continuous Security
Testing Platform, FR1919750997, added to this group by the
remainder census; its spec sheet's ADDENDUM §5 registered this
gap). Dispositions follow `../../gaps-batch/DECISION.md`;
platform-layer closures follow `../../PLATFORM-LAYER.md`.

**Entry-count verification (as briefed):** the section holds
exactly 1 inventory entry (idx 662) and GAPS.md lists exactly 1
`- [ ] open` entry in it — **no discrepancy** with the brief,
and no pre-closed entries in the section to reconcile.

Everything landed as ONE new module,
`src/cyber/extensions_addition.py` (`ExtensionAdditionStore`,
audit actions prefixed `exta_`), reusing the opaque-reference
validators from `cyber.extensions` (this package's own code;
reuse stated in the module docstring). All 9 pre-existing
modules — the 8 inherited core modules and the first batch
unit's `extensions.py` (`98c0362e…`) — are byte-identical
(SHA-256 verified against the pre-build record in
`scratch/prebatch-addition-src.sha256`; `store.py` still
`f692fc74…`). No core extension was needed. Tests:
`tests/test_gaps_batch_addition.py`. Suite: **225 → 246**, all
passing.

Tier discipline holds on the whole surface: this is an L1 build
— the extension writes to the founding build's plain append-only
audit log and reuses its permission matrix unchanged (program
registers `manage_assets`, engagement creates `manage_risks`,
lifecycle transitions `triage`, disclosure records `ingest`,
reads `read`). No hash chain, no lockout, and no auditor role
was imported downward from the L3 sibling. Category discipline
holds too: references are opaque tokens only (IP-shaped, URL,
and hostname values are rejected at the boundary, pinned by
test); no record, view, or summary computes a score (a recursive
key scan pins the absence of `score` keys — the founding build's
published deterministic finding and risk formulas in
`cyber.store` remain the only scoring in the package and are not
re-implemented here); every count and latest value derives at
read and is never a key on a stored record (pinned by test).

## Per-entry disposition

### idx 662 — reference (stub-engine, as drafted)

> Crowdsourced security testing & disclosure coordination platform: researcher-community marketplace, engagement management, and disclosure coordination (registered from the fork's described function; no taxonomy family exists for it — vulnerability management is scanning tooling and application security is testing engines, and a human researcher marketplace is neither. The findings its engagements produce are ingestible by the Core today)

Labeled reference implementation. The entry names a human
researcher marketplace and a platform operated against live
systems: recruiting, matching, and managing a community of
independent security researchers, running engagements against
customers' internet-accessible systems, and coordinating
vulnerability disclosure with them. None of that is a records
function this substrate can perform — there is no community
here to recruit, no researcher is matched or managed, no target
is tested, and no disclosure is coordinated with anyone. Its
honest form here is the reference surface, every record carrying
`reference_stub: True`:

- `register_program` (`program-`): a disclosure-program record —
  opaque `program_ref` and `scope_ref`, title as data, carrying
  `marketplace_operated_here` / `researchers_recruited_here` /
  `coordinated_here: False` on its face.
- `create_engagement` / `transition_engagement` (`eng-`): an
  engagement record bound to a registered program, the researcher
  named by opaque `researcher_ref` only, with the reported
  lifecycle `invited → active → completed` (plus `declined` /
  `cancelled` from `invited`, `cancelled` from `active`) tracked
  as the external platform reports it; `matched_here` /
  `tested_here: False`.
- `record_disclosure` / `transition_disclosure` (`disc-`): a
  disclosure record under an engagement — the finding it concerns
  named by opaque `finding_ref` only, its `reported_label` stored
  exactly as the external platform reported it (verbatim, never
  reproduced or computed), with the coordination lifecycle
  `reported → triaged → disclosed → closed` tracked as reported;
  `coordinated_here: False`.
- `program_view` / `engagement_view`: derive engagement and
  disclosure counts, engagements by status, and the latest
  reported disclosure label at read via the `_latest_label` seam;
  the stored program and engagement records carry none of the
  derived keys, pinned by test.
- `addition_summary`: counts only — programs, engagements,
  disclosures.

The findings such engagements produce are **not** created here:
as the entry's own text records, they are ingestible by the
founding Core today, in the same register scanner output lands
in (exercised in the fork's shape by the remainder addition's
substrate tests). A disclosure record names a finding by opaque
reference only; this module ingests, scores, and triages nothing.

## Re-judgments

None. The drafted stub-engine disposition held on close reading
against this group's spec: the ADDENDUM (§3, §5) already decided
that the fork claims no family and that the marketplace and the
coordination workflow are Extended, with only the findings'
landing place in Core — so the surface above is the labeled
reference form of the platform, not a records build of it. The
first unit's idx 170 re-judgment does not transfer: that family
had an honest records form *beyond the substrate* (a framework
register and an evidence workflow the substrate itself performs);
a human marketplace has no such form. Expected closure
arithmetic for the parent: **1 entry closed — 0 built,
1 reference, no token overrides.**

## Negative control

Fresh, for the new code: the latest-label seam
`ExtensionAdditionStore._latest_label`, mutated to an
earliest-reading form (`records[0][key]`, occurrence count
asserted = 1 before patching). The in-suite three-leg control
(`TestLatestLabelNegativeControl`: canonical latest /
earliest-reading mutant subclass / `assertRaises`) plus the live
drill: full suite under mutation ran **246 tests, exactly
5 failures**, all in `test_gaps_batch_addition.py` (the program
view's and engagement view's latest-label derivations and the
control's three legs), with all 225 pre-existing tests still
passing. Restored from `scratch/extensions_addition.py.premutation`,
SHA-256 verified identical (`c02aefe5…`), suite re-ran green.
Full record in `tests/README.md`; raw output in
`scratch/gaps_batch_addition_mutation_run.txt`, failure names in
`scratch/gaps_batch_addition_drill_failures.txt`.

## Honesty notes

- Nothing on this surface operates a marketplace, recruits,
  matches, or manages a researcher, tests or probes any system,
  coordinates a disclosure with anyone, or creates, ingests,
  scores, or triages a finding; the records are the labeled
  reference form of an external human platform, and its reported
  outcome labels are held verbatim.
- Not covered (stays as it stands, not closed by this unit): the
  section's explicitly-no-claimant notes stand as recorded in
  GAPS.md — application security testing engines, vulnerability
  scanners, and detection engines / staffed SOC gain no claimant
  from this unit, and nothing here double-books the fork's
  substance under any of them.
