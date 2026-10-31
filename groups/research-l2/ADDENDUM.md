# Addendum — Research, CMMC L2: the 5 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 5
previously uncategorized forks of remainder build unit
**`addition:research-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its
11-function core, and its control baseline are **unchanged**.
This document records what joined, what the newcomers claim under
the group's existing taxonomy, the core-delta decision for every
claimed function, and the updated union statement.

**Headline: forks spec'd 5 / 5; 2 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 85 → 97, all
passing.** The honest shape of the unit: this group's taxonomy
was defined from the Gen3 fork's own single platform sentence
(the Group 1 method for a brand-new category), so its patterns
are that sentence's literal phrases. Applied verbatim to five
different product kinds, it tags exactly one family —
`data_sharing`, twice — and **3 of the 5 newcomers claim zero
families**. That outcome is pinned in tests, itemized in §2, and
recorded here rather than repaired by re-tuning. **9 new gap
functions** are named in §5 (the newcomers' own engines, which
the taxonomy was never built to tag), and 2 already-registered
gaps gain claimants.

## 1. Membership and method

The 5 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2000939520` | Broad Institute, Inc. / Terra |
| 2 | `FR2104636677` | Ipsos America, Inc. / Ipsos Research |
| 3 | `FR2204842850` | Rosalind, Inc. / ROSALIND |
| 4 | `FR2033152148` | Seven Bridges Genomics, Inc / Seven Bridges Platform |
| 5 | `FR1924344515` | Wellspring Worldwide, Inc. / Wellspring Tech Transfer and IP Management Suite (WTIMS) |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **imports the original `scratch/extract.py`'s taxonomy
  and asserts its literal copy of the (id, label, regex) triples
  equal to the original's before tagging** — the taxonomy was
  applied verbatim, not re-tuned for the newcomers. Same sentence
  splitting, same evidence rule (first matching sentence per
  family, stored verbatim), same sheet schema. The 5 sheets are
  **appended** to `specs/specs.json` after the original 1, which
  is byte-for-byte untouched (the file re-serializes identically
  for the original entry under the original extractor's own
  settings — `json.dump`, indent=1, trailing newline — and is
  byte-preserved through the first sheet's closing brace;
  verified in the build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 5
  descriptions were present; no live fetching. All 5 are FedRAMP
  **Moderate**, so the group stays single-tier and the L2
  baseline is inherited in full (Merge Rules 1–2), unchanged.
  All 5 source records carry `business_categories: []` — they
  were uncategorized in the source; their Research category is
  the census's description-based proposal, recorded in the
  sheets as `deadramp_category`, never dressed up as a source
  fact.
- The census starting point was verified, not trusted: all **8
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **8 / 8 verify** as verbatim
  substrings.
- **No exclusion trap applies to the newcomers.** None of the 5
  records carries a hosted-services block: every record's
  `certified_services` field is empty and no "not authorized"
  segment exists in any of the 5 descriptions (asserted in the
  extractor). Only `service_desc` was matched, per house method.

## 2. What the additions claim

**2 claims** across the 5 forks; 2 of 5 carry a claim, and both
claims are the same family. Claim counts per family among the
additions, with the group's combined count (original 1 +
additions = 6 forks) alongside:

| Function | Additions claiming | Group total (6) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Data sharing | 2 | 3 | **Core slice** — sharing transacted as request / decision / grant records; delivery engine Extended |
| Data commons development, configuration & operation | 0 | 1 | **Core** — commons registry |
| Data ecosystems / data meshes | 0 | 1 | **Core** — commons record kinds |
| Workspaces | 0 | 1 | **Core** — workspace registry |
| Data management (managing data) | 0 | 1 | **Core** — dataset registry |
| Data analysis (analyzing data) | 0 | 1 | Extended — analysis engines |
| Open access & controlled access data | 0 | 1 | **Core** — tier designation on dataset records |
| Open-source platform (platform note) | 0 | 1 | Platform note |
| Multi-tenant SaaS delivery (platform note) | 0 | 1 | Platform note |

Per-fork claim counts: Terra **1**, ROSALIND **1**, Ipsos
**0**, Seven Bridges **0**, Wellspring **0**. The full per-fork
table is pinned literally in `tests/test_additions.py`
(`EXPECTED_CLAIMS`).

### Zero-claim forks — pinned, not hidden

Three additions carry **zero claims**, for the same reason the
Legal & Policy newcomers did: this taxonomy's patterns are the
original fork's literal phrases, and a different product kind in
the same category matches none of them.

- **Ipsos Research** (`FR2104636677`) — a multi-modal survey
  research and AI-analytics platform. Its verbs are "manage"
  and "managed", its noun is "analysis"; the taxonomy requires
  "managing" and "analyzing". The census citation itself
  ("end-to-end support for the entire research lifecycle, from
  survey design and deployment to advanced, AI-driven
  analysis") tags nothing.
- **Seven Bridges Platform** (`FR2033152148`) — a bioinformatics
  analysis platform. "store, analyze, and jointly interpret
  their bioinformatic data" contains none of the taxonomy's
  verbs: "analyze" is not "analyzing", and "store" alone fires
  no family.
- **Wellspring WTIMS** (`FR1924344515`) — a technology transfer
  and IP management suite. It writes "manage", "Manages", and
  "management" throughout, never "managing"; its SaaS and
  multi-tenant properties appear in separate clauses, never as
  the taxonomy's contiguous spelled-out phrase.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Terra** — "analysis" appears throughout ("secure and
  scalable analysis", "interactive analysis tools") but never
  "analyzing": no `data_analysis`. The word **"workspaces" —
  Terra's own product concept — never appears**; the description
  writes "sharing work selectively", which is its `data_sharing`
  claim instead. "access datasets sponsored by partner
  organizations that are hosted" is not the tier family's
  literal "open access and controlled access data". "upload
  their data to the cloud" fires nothing — ingestion is not a
  family in this taxonomy, and the dataset registry is
  metadata-only by design. "repository of best-practice,
  ready-to-use bioinformatics workflows" matches no pattern.
- **Ipsos** — "We manage the complete paper survey lifecycle"
  and "All data is managed within our secure GovCloud
  environment" are not "managing". "AI-driven analysis",
  "AI-Powered Data Analytics", and "advanced … analysis" are
  not "analyzing". "a full range of data collection methods"
  matches no family — this taxonomy has no collection family.
  The LLM capability list (classify verbatims, extract insights,
  flag PII, generate summaries) is engine surface with no
  records family to land in; it is gap-named in §5.
- **ROSALIND** — "securely analyze and interpret datasets" is
  not "analyzing". "multi-tenant SaaS solution" is not the
  spelled-out "multi-tenant Software as a Service". "knowledge
  management" is not "managing", and there is no knowledge
  family. "scientific collaboration" matches no family — this
  taxonomy has no collaboration family. "permissions-based data
  sharing between authorized users and across institutions"
  fires `data_sharing` but not the tier family, whose pattern
  is the Gen3 sentence's own "open access and controlled access
  data" — recorded as a near-miss, not tuned into a claim.
- **Seven Bridges** — "a central hub for teams" is not
  "workspaces". "The Platform co-locates analysis pipelines
  alongside the largest genomic datasets" — "analysis", not
  "analyzing". "allocates storage and compute resources on
  demand" matches no family; the allocation engine is
  gap-named in §5.
- **Wellspring** — "delivered as a SaaS offering using a
  multi-tenant Government Community cloud computing environment"
  carries both properties but never the contiguous phrase.
  "seamless data integrations" matches no family — this
  taxonomy's only integration-adjacent family is `data_sharing`,
  which requires "sharing". "streamlines technology transfer
  and IP management from invention disclosure through licensing
  and commercialization" is the suite's core surface and tags
  nothing; it is gap-named in §5.

### Wording artifacts in claims that stand

None requiring correction — both `data_sharing` claims rest on
the word "sharing" used in its plain sense. One splitter note,
recorded plainly: ROSALIND's evidence sentence is a bullet-list
chunk produced by the house sentence splitter (the description's
list items are not period-terminated), so the stored evidence
carries its list marker and the full bullet text. That is the
same splitter behavior as the original pass, and the evidence is
verbatim either way.

## 3. Core-delta decisions

Only one family gains claimants, and its disposition was already
decided in UNION-SPEC. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Data sharing (2) | Core slice 5/6/7 — requests, decisions, grants | **Carried** — no change |

**Result: the core is unchanged.** Terra's "sharing work
selectively, protecting data from unwanted re-distribution" and
ROSALIND's "permissions-based data sharing between authorized
users" both presuppose exactly the records forms the build
already holds: a controlled dataset record with its tier
designation, an access request, a decision by someone who is
not the requester, and a time-boxed grant. Nothing either claim
presupposes is missing, and the delivery remainder stays the
already-Extended *data delivery / transfer engine* gap, which
gains both forks as claimants (§5). `src/` is byte-identical to
the shipped build (`src/research/store.py` SHA-256
`ff43a9acc78d6a65b527632c69923c91c5cfdb3716bc63d9efe56103d04bb417`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction. The privacy discipline is unchanged and now
exercised against the newcomers too: every dataset record in
the additions tests is metadata + checksum under the pinned key
set, and grants remain records that confer nothing.

## 4. Updated union statement

The group now covers **6 forks** (1 original singleton + 5
remainder additions), **11 claims** in total (9 + 2), with **3
of 6** forks carrying at least one claim. The merged build
remains the same 11-function research-data records substrate —
commons registry, organization registry, workspace registry,
dataset registry (metadata + checksums only), access requests,
decisions, derived-status grants, search & summary, API, RBAC,
append-only audit — now spec'd against 6 marketplace offerings
instead of 1. The group's character changes more than its
substrate: the singleton spec said Research "is also the entire
category" — true of the filed registry, but the census
reclassification brings in five more offerings whose own
descriptions are research platforms: three genomics data
platforms (Terra, ROSALIND, Seven Bridges), a survey-research
platform (Ipsos), and a technology-transfer suite (Wellspring,
whose research-institution surface is its market). The taxonomy
born from one platform sentence tags only the sharing family
among them, and the union says so plainly: the newcomers' real
surfaces are the engines named as gaps in §5, and this build is
their records substrate, not a substitute for any of them.

## 5. Gaps — for the registry at ship

**New gap functions** (9), all fork-excess engines — the
newcomers' own operating surfaces, which the taxonomy was never
built to tag and no claim presupposes as records:

- **Interactive analysis environment & workflow execution
  engine** (interactive analysis tools incl. JupyterLab /
  Jupyter integration, a repository of ready-to-use
  bioinformatics workflows, data exploration interfaces over
  hosted partner datasets) — Terra
- **Bioinformatics analysis pipeline engines** (NGS and
  multi-omic analysis pipelines — RNA-seq, ATAC-seq, ChIP-seq,
  proteomics; pipelines co-located with large genomic datasets)
  — ROSALIND, Seven Bridges
- **Diagnostic monitoring & variant surveillance platform**
  (real-time SARS-CoV-2 variant surveillance and diagnostic
  monitoring, BioBank sample tracking, test-panel workflows)
  — ROSALIND (DxM)
- **Knowledge-graph storage & searchable library engine**
  (institutional data held as knowledge graphs, searchable
  libraries) — ROSALIND
- **Elastic storage & compute allocation engine** (on-demand
  allocation of storage and compute resources for analyses)
  — Seven Bridges
- **Multi-modal survey research platform** (survey design and
  deployment across digital and paper channels; paper survey
  lifecycle — printing / mailing logistics, high-speed scanning
  and data capture) — Ipsos
- **AI analytics engine over LLMs** (verbatim classification,
  insight extraction, PII flagging and redaction support,
  executive summarization of survey text) — Ipsos
- **Technology transfer & IP management suite** (invention
  disclosure through licensing and commercialization workflows,
  IP and contract management, disclosure and project
  submissions) — Wellspring
- **Document generation & electronic-signature workflow
  engines, and external integration components** (DocGen PDF
  generation, DocSign signer workflows, iEdison API push,
  migration tooling) — Wellspring (fork excess; the integration
  components are platform-specific to the fork's Salesforce
  hosting)

**Existing gaps gaining claimants:**

- **Data delivery / transfer engine for sharing** — +2: Terra,
  ROSALIND (the additions' `data_sharing` claimants; their
  sharing is transacted as records in Core, and delivery stays
  Extended — grants confer nothing and no data moves).
- **Query & analysis workspace engines** — +3 by substance:
  Terra, ROSALIND, Seven Bridges. Analysis is their headline
  activity, but the `data_analysis` family claim itself did
  not fire on any of them ("analyze" / "analysis", never
  "analyzing"), recorded in §2 — the gap gains them by
  substance, not by claim.

**Platform notes:** multi-tenancy is asserted by ROSALIND and
Wellspring of their own platforms; the build remains a
single-tenant reference deployment, as with the original fork's
platform note. Wellspring's Evolve component runs inside
Salesforce Gov Cloud — a third-party platform dependency of the
fork, outside this build.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the literal
  per-fork claim table, the zero-claim fork and family sets,
  verbatim evidence, the census citations, and the near-miss
  pins (see `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: the full sharing flow with grant derivation at
  three clocks and verify-by-content (Terra); the open-tier
  request rejection and grant revocation beating the window
  (ROSALIND); the pinned dataset key set with verify-by-content
  and summary counts (Ipsos); workspace + tier-filtered dataset
  listing, search, and the non-member boundary (Seven Bridges);
  the pinned organization shape, duplicate-ref rejection, and
  read-computed summary counts (Wellspring).
- **Tests: 85 → 97, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `_derive_grant_status`
  in `src/research/store.py` was patched to return `"active"`
  unconditionally and the full suite ran — **97 tests, exactly
  9 failures**: the original drill's 7 (grant derivation ×3,
  negative control ×2, reporting summary, service full flow)
  plus 2 from the new additions module (the Terra sharing-flow
  derivation case and the ROSALIND revocation case), which trip
  on the mutant exactly as designed. `store.py` was restored
  from the pre-mutation copy and verified SHA-256-identical to
  the shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
