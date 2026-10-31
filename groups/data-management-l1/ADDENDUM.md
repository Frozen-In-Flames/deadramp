# Addendum — Data Management, CMMC L1: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:data-management-l1`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its
12-function carried core, its core-boundary decision, and its
control baseline are **unchanged**. This document records what
joined, what the newcomer claims under the group's existing
taxonomy (nothing), the core-delta decision, and the updated
union statement.

**Headline: fork spec'd 1 / 1; 0 new claims — a zero-claim fork,
in a group whose only fork was already zero-claim, so the group
now stands at 0 claims across 2 forks; core delta — zero
functions extended, `src/` byte-identical; tests 196 → 207, all
passing.** The newcomer is a monitoring-and-evaluation (M&E)
results platform whose marketplace description is written in the
vocabulary of its domain — data capture, analysis, reporting,
measuring progress — and that vocabulary fires **no pattern in
any of the 19 families**: the census's two classification
citations both verify as verbatim text and both tag nothing.
**2 new gap functions** are named in §5; 2 existing gaps gain a
member by substance; no existing gap gains a claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2100845343` | DevResults / DevResults |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact (id, label, regex)
  triples** — and, because this group's taxonomy is inherited
  from the parent group, the extractor also parses the taxonomy
  out of `groups/data-management-l2/scratch/extract.py` and
  **asserts the two are equal**: the verbatim-inheritance proof,
  not a claim about it. Same sentence splitting, same evidence
  rule (first matching sentence per family), same 400-char
  evidence truncation, same sheet schema.
- **Reproduction before tagging:** the extractor first rebuilt
  the original fork's sheet from the raw cache with the original
  construction, and it came out **deep-equal to the shipped
  sheet, claim table included** (empty, as shipped — the shipped
  table is the ground truth and it reproduced exactly). Only
  then was the newcomer tagged. The new sheet is **appended**
  after the original, which is byte-for-byte untouched (the
  re-serialized file is byte-preserved through the original
  sheet's closing brace; asserted in the extractor, on top of
  the parsed deep-equality).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. No live
  fetching. The fork is FedRAMP **LI-SaaS / Certified** (SaaS,
  Public Cloud) — the group's second LI-SaaS member. LI-SaaS is
  FedRAMP's tailored subset of the Low baseline, so the L1
  baseline is inherited in full, unchanged.
- **Category provenance, stated plainly:** forks.json files this
  fork as "Uncategorized (none in source)" and its source record
  carries an **empty** business_categories list. The census
  assigned Data Management from the fork's own description, and
  that assignment is what this unit extends; the sheet records
  `deadramp_category: "Data Management"` on that basis.
- The census starting point was verified, not trusted: both
  **census citations** for this fork were re-checked against the
  fork's own cached description and **2 / 2 verify** as verbatim
  substrings — with the twist recorded in §2: both tag nothing.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty (asserted in the
  extractor), its description contains no third-party catalogue
  and no scope-exclusion segment (scanned; markers recorded in
  `scratch/additions_sentence_map.json`), and only `service_desc`
  was matched, per house method. **No raw hit was removed: there
  were no raw hits at all.**

## 2. What the addition claims

**0 claims — 0 raw hits across all 19 families, before any
correction question can arise.** The fork's description is four
sentences long; the per-sentence map is
`scratch/additions_sentence_map.json`, and every sentence's
family list is empty. The group's claim total is unchanged at
**0** (Pagefreezer 0, DevResults 0). This group's character does
not change — it sharpens: it was a singleton whose one fork
evidenced nothing under the verbatim taxonomy, and it is now a
two-fork group in which *neither* fork does. Zero is reported as
the floor it is; the taxonomy was not loosened, and no function
was invented for this fork either.

### Near-misses, itemized per sentence

- **Sentence 1** ("DevResults is a web application with tools
  for data capture, analysis, reporting, visualizations, project
  management, and team collaboration.") — this is the census's
  first classification citation and it tags nothing.
  `ingestion_collection` requires "data collection" /
  "collecting information" / "ingest" / "stream content"
  phrasing; **"data capture" is none of them** — the classic
  synonym, and still a miss under the verbatim patterns.
  `query_reporting` requires "query and report", "report
  visualization", "analytics", or "business intelligence"; the
  sentence has "analysis" (not "analytics" — the token differs
  at the character level), "reporting" (not the contiguous
  "report visualization" — a comma intervenes before
  "visualizations"), and no query token. "Project management"
  and "team collaboration" are other categories' functions,
  asserted in this sentence and booked nowhere in this group
  (see §5) — this taxonomy has no family for them and none is
  improvised.
- **Sentence 2** ("DevResults was designed to streamline
  fragmented data processes into a single proven system,
  allowing for the utilization of data for decision making
  across activities and throughout government agencies,
  non-profit organizations, and private sector companies.") —
  the census's second citation, also tagging nothing.
  `integration_exchange` requires an integration / connectivity /
  connecting token; "streamline fragmented data processes into
  a single proven system" is consolidation asserted in
  substance with none of the family's tokens present.
  `dataset_registry` requires dataset / registry / repository /
  records-management phrasing; "data processes" and "a single
  proven system" are none of them. "Utilization of data for
  decision making" is the purpose the query/reporting substance
  serves (booked by substance under that gap in §5), not a
  family token.
- **Sentence 3** ("Over the past decade, DevResults has
  supported partners with managing data, measuring progress,
  and learning from the results.") — "managing data" carries no
  registry, collection, or governance token; "measuring
  progress" is the fork's M&E domain function, for which the
  taxonomy has no family (see §5). Tenure prose ("over the past
  decade") is marketing and tags nothing, as it should.
- **Sentence 4** ("DevResults will allow users across an
  organization and around the world to better utilize data for
  management and decision-making.") — no family token of any
  kind; "users across an organization" tags neither governance
  nor access (no governance / controls / API phrasing), and
  global reach is the fork's deployment prose, not a hosting
  claim (`platform_hosting` requires private-cloud /
  scalable-compute / platform-offering phrasing; none present).
- **Whole-description absences** — there is no "search" token
  (`catalog_search`), no retention / disposition / NARA token,
  no API token, no AI/ML token, no accuracy/completeness token
  (`quality_validation` — "measuring progress" is not a data
  quality assertion), and no workflow token. Whatever the
  platform does in the world, its marketplace description says
  it in domain terms the governance-taxonomy does not read.
  Reputation is not evidence.

**The census-citation twist, again in its pure form.** Both
census citations verify as verbatim description text — they are
the description's first two sentences — and **both tag
nothing**. The census classified the fork correctly by reading
those sentences for substance; the claim pass reads the same
sentences for function tokens and finds none. Verification is
not a claim, in both directions, and classification is not a
claim either.

## 3. Core-delta decision

The newcomer claims no family, so there is no claimed function
missing a records form and no form is added on the strength of
unclaimed prose. Per family, the decision is uniform: **every
one of the 19 families keeps the disposition the union spec's
table already gives it** (Core-carried, Core slice, or Extended)
— no family moves to "core extension specified" on this
addition, and the functions the newcomer asserts in substance
are booked as gaps in §5, not built. **Result: the core is
unchanged — delta zero functions.** The substrate the fork's
described operation presupposes — partner results held as
registered datasets with versioned schemas, arrivals recorded
as ingestions from registered sources with provenance, access
to the consolidated set governed by purpose-bound requests that
are never self-approved, and the set leaving under checksummed
export manifests — is the substrate the build already is,
exercised in the newcomer's shape by the additions substrate
tests and recorded as **carried, not claimed**, exactly as the
union spec's core-boundary decision frames it for the original
fork. `src/` is byte-identical to the shipped build (all 7
`datamgmt` modules SHA-256-verified against the pre-work hashes,
the mutation drill included; `src/datamgmt/store.py` remains
`dc35677ccdaf4d416a10a5364128f54bb1b1802fd8a99c00271ad081caf2774e`,
the hash the shipped tests/README records for it). The tier
baseline does not change: the group was LI-SaaS 1 and is now
LI-SaaS 2, and LI-SaaS adds nothing to the Low union.

## 4. Updated union statement

The group now covers **2 forks** (the original singleton + 1
remainder addition), **0 claims** in total (unchanged), with
**0 of 2** forks carrying a claim. The merged build remains the
same 12-function governance substrate — dataset registry,
catalog search, source registry, ingestion records, provenance,
data quality, access governance, retention schedules, export
manifests, REST API, RBAC, and the append-only audit log —
carried at the Low/L1 baseline under the core-boundary decision,
now spec'd against 2 marketplace offerings instead of 1. The
honesty posture of the group is likewise unchanged and now
doubly evidenced: two unrelated products (a website archiver
and an M&E results platform) sit in this category at this tier,
the category substrate is carried for both, and neither
description evidences a single function under the taxonomy the
category itself chose. The claims floor for the category at L1
is zero, stated rather than padded.

## 5. Gaps — for the registry at ship

**New gap functions** (2), both registered from the fork's
described function, not from a claim:

- **M&E / results-management platform functions** — indicator
  and results frameworks, results tracking, and progress
  measurement as a domain application, asserted across the
  description ("tools for data capture, analysis, reporting",
  "supported partners with managing data, measuring progress,
  and learning from the results"). No taxonomy family covers
  the domain application: the families are governance-substrate
  families, and an M&E platform's results framework is a domain
  application built on such a substrate, not the substrate
  itself. The records its operation presupposes (registered
  datasets, ingestion records, exports) are Core today; the
  results framework is Extended.
- **Data-capture tooling & collection instruments** — the
  capture side of the described platform ("tools for data
  capture"), i.e. the instruments by which programme data is
  captured at the point of origin. The Core records ingestions
  from registered sources but ships no capture instrument.
  Distinct from the two capture-adjacent gaps already
  registered: Pagefreezer's web crawling & snapshot capture
  engine (capture of *web pages*, this group's original gap)
  and the category's guided-interview engine (adaptive
  interviews, Group 12's list). This is general-purpose capture
  tooling for programme data; neither existing gap describes
  it.

**Existing gaps gaining a member by substance** (claim-level
positions unchanged — no family fired):

- **Query & visualization engines** (registered in the union
  spec's carried category list: live query against source data
  and in-workflow report rendering) gains the fork by
  substance: "analysis, reporting, visualizations" and
  "utilization of data for decision making" assert exactly
  this function in the fork's own words. The family claim did
  not fire ("analysis" is not "analytics"; no contiguous
  "report visualization"), so the gap gains a member, not a
  claimant. The decision-support purpose is booked here once,
  not double-booked as a separate gap.
- **Integration runtime & connector engine** (registered in the
  union spec's carried category list) gains the fork by
  substance: "streamline fragmented data processes into a
  single proven system" is consolidation of fragmented data
  processes asserted as the product's design purpose. The
  family claim did not fire (no integration/connectivity
  token), so again: a member by substance, not a claimant.

**Explicitly no claimant, and booked nowhere in this group:**

- **Project management & team collaboration** — asserted in
  sentence 1 in so many words. They are not Data Management
  functions; they belong to the Operations Management and
  Collaboration groups' builds. Recorded here so the sentence
  is fully accounted for, and deliberately *not* registered as
  a gap of this group: a gap registry that absorbs every
  neighbouring function a description mentions stops meaning
  anything.
- **Storage / database engines** — the category's standing
  named absence is untouched: "a single proven system" is not
  a storage or database assertion, and no storage token exists
  in the text.
- **Field-level / transformation lineage** — the category's
  second standing named absence is untouched: no lineage token
  exists; the build's provenance remains at ingestion
  granularity.
- Every other Extended family is untouched: the newcomer's
  prose contains no token for any of them, claimed or otherwise
  (§2's whole-description absences). All 19 families remain at
  **0 of 2**.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  tables (the newcomer's empty table and the original's exactly
  as shipped), the zero-claim set (all 19 families), verbatim
  census citations tagging nothing, registry fields as
  published, the near-miss pins, and the group totals (2 forks /
  0 claims / 0 of 2 claiming / composition LI-SaaS 2) — see
  `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a partner-results flow — a "Partner Activity Results" dataset
  with an indicator/value schema, a manual field-reports source,
  a completed ingestion of 1,200 records and a failed one of 50,
  provenance counting completed runs only, an export manifest
  carrying the canonical checksum, catalog search finding the
  dataset by tag and by schema field name — and an
  access-governance flow in the fork's shape, in which carol's
  request for the results dataset cannot be decided by a
  decider carrying her own name, stays requested with no grant,
  and is then approved by the steward, minting exactly one
  grant to carol. Both are carried-substrate cases: the fork
  claims no family, and the addendum claims none on its behalf.
- **Tests: 196 → 207, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the self-approval
  guard in `DataMgmtStore._check_decider_not_requester`
  (`src/datamgmt/store.py`) was patched to a no-op
  (`return None`) — the exact mutation the shipped drill record
  names, applied as a scoped replacement of the guard's body
  with the target text asserted to occur exactly once — and
  the full suite ran: **207 tests, exactly 5 failures** — the
  shipped drill's 4 plus exactly 1 from the new additions
  module
  (`test_additions.TestDevResultsSubstrate.test_access_to_results_dataset_is_never_self_approved`),
  tripping exactly as designed. `store.py` was restored from
  the pre-mutation copy and verified SHA-256-identical to the
  shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`, raw list in
  `scratch/additions_mutation_run.txt`.
