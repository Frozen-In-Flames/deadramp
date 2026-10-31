# Addendum — Legal & Policy, CMMC L2: the 6 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 6
previously uncategorized forks of remainder build unit
**`addition:legal-policy-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 13-function
core, its control baseline, and its Extended dispositions are
**unchanged**. This document records what joined, what the newcomers
claim under the group's existing taxonomy, the core-delta decision
for every claimed function and for the newcomers' own functional
surface, and the updated union statement.

**Headline: forks spec'd 6 / 6; 0 new claims — every newcomer
claims zero of the 11 families under the taxonomy applied verbatim;
core delta — zero functions extended, `src/` byte-identical; tests
94 → 106, all passing; 10 new gap functions** (the newcomers'
eDiscovery, signature, and contract platforms, §5).

## 1. Membership and method

The 6 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1506246782` | Complete Discovery Source / Complete Discovery Source Federal Cloud (CDS-F) |
| 2 | `F1210161615` | Deloitte / Evidence Management System (EMS) |
| 3 | `F1609267945` | DocuSign / Docusign - IAM eSignature |
| 4 | `F1605027893` | DocuSign / DocuSign CLM |
| 5 | `FR1800263217` | Innovative Discovery, LLC / Innovative Driven Government Cloud (IDGC) |
| 6 | `FR2004753002` | Relativity ODA LLC / RelativityOne Government |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/extract_additions.py`,
  which carries a copy of the group's original
  `scratch/extract.py` taxonomy and **asserts the copy is identical
  to the original's `TAXONOMY` before tagging** — the taxonomy was
  applied verbatim, not re-tuned for the newcomers. Same sentence
  splitting, same evidence rule (first matching sentence), same
  sheet schema. The 6 sheets are **appended** to
  `specs/specs.json` after the original sheet, which is preserved
  (deep-equality against git HEAD verified in the build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 6
  descriptions were present; no live fetching. All 6 are FedRAMP
  **Moderate** / FedRAMP Certified, so the group stays single-tier
  and the L2 baseline is inherited in full (Merge Rules 1–2),
  unchanged.
- The census starting point was verified, not trusted: all **9
  census citations** for these forks were re-checked against the
  forks' own cached descriptions — **9 / 9 verbatim** (none needed
  whitespace normalization). The citations are also pinned in
  `tests/test_additions.py` against the sheets' descriptions.
- All 6 forks carry an empty `business_categories` list in the
  source — they are in this category because the census assigned
  them from their own descriptions (legal document services,
  litigation and evidence support, agreements), never from a
  filing label.

## 2. Claim ranking — the enlarged union (7 forks)

The taxonomy was defined from the original fork's own description
(the Group 1 method, `UNION-SPEC.md`): its 11 patterns are that
fork's own phrases. Applied verbatim, **no newcomer sentence
matches any pattern**, so every family's claimant count is
unchanged. This is the honest outcome of the method — the same
discipline that left 14 of 20 Operations Management additions and
3 of 18 Cybersecurity additions at zero claims — stated here in
full rather than tuned away: the newcomers are eDiscovery,
evidence-management, e-signature, and contract-lifecycle
platforms, a different functional surface from an AI agent
workspace over a curated legal library.

| # | Function | Forks claiming (of 7) | Additions claiming | Disposition (unchanged) |
|---|---|---:|---:|---|
| 1 | AI agent workspace | 1 | 0 | Core slice (workspace & session records); runtime Extended |
| 2 | Curated legal library | 1 | 0 | Core (source registry); corpus content Extended |
| 3 | Full-text and semantic search | 1 | 0 | Core slice (digest search records); engines Extended |
| 4 | Secure single-use agent sandboxes | 1 | 0 | Core slice (single-use rule); runtime Extended |
| 5 | Code execution | 1 | 0 | Core slice (execution records); engine Extended |
| 6 | Document generation | 1 | 0 | Core slice (document records); engine Extended |
| 7 | Agency user management | 1 | 0 | Core (agency registry, membership, RBAC) |
| 8 | Session audit visibility | 1 | 0 | Core (append-only audit, admin-gated read) |
| 9 | Usage export | 1 | 0 | Core (usage records + export manifests) |
| 10 | Identity federation & MFA | 1 | 0 | Platform note — hooks, not an IdP |
| 11 | SaaS delivery | 1 | 0 | Platform note — single-tenant reference deployment |

One wording fact is recorded plainly: all six newcomers **are**
SaaS offerings (the source's service model says so for each), yet
`saas_delivery` gains no claimants, because the family's pattern
is the original product's own identity clause ("SaaS AI
platform") and no newcomer uses it. The platform disposition
stands on the original fork's claim alone; the merged build's
deployment shape is unaffected.

### Per-fork near-misses (why zero, fork by fork)

- **CDS Federal Cloud** — "advanced analytics" matches nothing:
  this taxonomy has no analytics family. Relativity and Clearwell
  are named as hosted third-party technologies — component
  naming, which the original extractor's infrastructure rule
  already excludes. "SSAE 16 Type 2 audited data centers" is
  assurance prose about its own facilities, not
  `session_audit_visibility`.
- **Deloitte EMS** — NavigAite is a "Generative AI solution" built
  on "a Large Language Model (LLM)", but no sentence says "AI
  agent workspace": it is an AI feature of a review offering, not
  the workspace family. "summarize, classify, and redact" never
  becomes the phrase "document generation" — those outputs are
  analysis, registered as a gap in §5. "Software-as-a-Service
  (SaaS)" is not the pattern "SaaS AI platform".
- **DocuSign IAM eSignature** — "user identity management" is not
  "agency user management": a different phrase, and a product-side
  identity feature for signers rather than an agency
  administration console. "authentication services" carries no
  federation language — the `identity_federation` pattern is
  "identity and access are federated". "SaaS application" is not
  "SaaS AI platform".
- **DocuSign CLM** — "advanced workflows that automate manual
  tasks" matches nothing: this taxonomy has no workflow family at
  all (its automation lands in §5). "document and contract
  management" matches neither the `legal_library` phrase nor
  "document generation".
- **IDGC** — "legal document services" and the eDiscovery list
  ("processing, document review, advanced analytics, assisted
  review, legal hold services, and production") match neither the
  `legal_library` pattern (the original fork's full
  curated-library phrase) nor `search` (no "full-text and semantic
  search"). Relativity and Nuix are named components — the
  infrastructure rule again. "Software as a Service (SaaS)
  offering" is not "SaaS AI platform".
- **RelativityOne Government** — "advanced searching and
  analytics" is not "full-text and semantic search" ("searching"
  is not the pattern phrase). "Machine learning" is a feature of
  the review platform, not an "AI agent workspace". Its
  extensibility ("apps built by our ecosystem of Relativity
  developer partners") is part of the review-platform gap in §5,
  not a separate family.

## 3. Core-delta decisions — the 11 families

For every family: **additions claimants 0 → carried; the original
disposition stands and nothing is extended.** No newcomer claim
presupposes a records form the build lacks, because there are no
newcomer claims. The substrate's existing registries are the
records forms the newcomers' activity would take in an embedding
— documents as metadata + SHA-256 records with verify-by-content
(Core 7/8), searches as digest-only records (Core 6), platform
usage as usage records and export manifests (Core 9/10) — and the
additions test module exercises exactly those forms, one substrate
case per newcomer, against the unchanged core.

## 4. Core-delta decisions — the newcomers' own surface

The newcomers' functions arrive as platforms and services, none
of them asserted by a taxonomy family. Each was decided on the
addition discipline (engines and platform workflows are Extended;
only a records form the union presupposes and lacks could extend
the core):

- **eDiscovery processing, review, production** (CDS, Deloitte,
  IDGC, RelativityOne) — engines and hosted platforms, Extended
  (§5). Their records surface (documents, searches) is already
  Core, per §3.
- **Legal hold & preservation** (Deloitte's EDRM "preserving",
  IDGC's "legal hold services") — **considered as a records form
  and decided Extended**: it arrives only as a service line inside
  eDiscovery platforms, is asserted by no taxonomy family, and
  its substance (hold-notice issuance, custodian tracking and
  acknowledgment) is platform workflow, not a registry the union
  presupposes — the same call the Operations Management addition
  made for case-management platforms. Registered as its own gap
  in §5 so the decision is visible, not defaulted.
- **Electronic signature** (DocuSign) — a signing engine
  (ceremony, cryptographic binding, validity under ESIGN /
  eIDAS), Extended. A signed exchange leaves a document record +
  usage in the substrate; the substrate signs nothing.
- **Contract lifecycle management** (DocuSign CLM) — a platform
  (authoring, negotiation, clause and obligation lifecycles),
  Extended. Its records surface is the document registry.
- **Agreement workflow automation** (both DocuSign offerings) —
  an execution engine over definitions, Extended, consistent with
  every group's workflow-registry-never-executes rule.
- **Identity** — DocuSign's product-side "user identity
  management" and "authentication services" change nothing at the
  platform layer: the build still ships RBAC hooks, not an IdP,
  and IA-2 stays with the embedding organization.

## 5. Gaps — new with the additions (for the GAPS.md registry)

All ten are **new** gap functions (none was registered under
Group 49); the parent registers them in `GAPS.md` at ship.

- [ ] open — **eDiscovery processing & collection engine** —
  ESI ingestion and processing, data collection across sources
  (mobile devices, social media, websites, O365), Nuix-class
  processing (CDS Federal Cloud, Deloitte EMS, IDGC)
- [ ] open — **eDiscovery document review platform** — hosted
  review over document collections, including Relativity /
  Clearwell hosting and the RelativityOne platform with its app
  ecosystem (CDS Federal Cloud, Deloitte EMS, IDGC,
  RelativityOne Government)
- [ ] open — **eDiscovery production, disposition & archiving
  engine** — producing, dispositioning, and archiving per the
  EDRM lifecycle (Deloitte EMS, IDGC)
- [ ] open — **Legal hold & preservation management** — hold
  issuance, custodian tracking, EDRM preservation (Deloitte EMS,
  IDGC); decided Extended per §4
- [ ] open — **AI document analysis for discovery** — generative
  summarization, classification and redaction (Deloitte
  NavigAite), assisted review / predictive coding, advanced
  analytics, machine learning and visualizations (Deloitte EMS,
  IDGC, RelativityOne Government, CDS Federal Cloud)
- [ ] open — **OCR & document extraction engine** — OCR with
  LLM-based data extraction and redaction identification
  (Deloitte EMS SmarText)
- [ ] open — **FOIA & disclosure release engine** — request
  response and release production for FOIA / disclosure
  (Deloitte EMS SecureRelease)
- [ ] open — **Electronic signature engine** — signing ceremony,
  signature binding and validity, envelope and transaction
  workflow (DocuSign IAM eSignature)
- [ ] open — **Contract lifecycle management engine** —
  contract authoring, negotiation, clause and obligation
  lifecycles across the agreement cloud (DocuSign CLM)
- [ ] open — **Agreement workflow automation engine** —
  workflow automation over signatures and contracts
  (DocuSign IAM eSignature, DocuSign CLM)

The original 9 Extended gaps of `UNION-SPEC.md` (AI agent
runtime, legal corpus content, full-text & semantic search
engines, sandbox runtime, code execution engine, document
generation engine, IdP / federation service, platform security
monitoring, FIPS-validated cryptography) gain **no** claimants
from the additions and stand as registered.

## 6. Updated union statement

The union is now **7 forks**: the original AI agent workspace
(VulcanGov) and six legal-services platforms the source left
uncategorized — three eDiscovery / evidence offerings (CDS
Federal Cloud, Deloitte EMS, IDGC), the eDiscovery platform they
largely run on (RelativityOne Government), and the two agreement
offerings (DocuSign IAM eSignature, DocuSign CLM). The census
filed all six under Legal & Policy from their own descriptions,
and they join the spec on that basis. They share the category and
the tier — and nothing else functional: under the group's
taxonomy they claim zero families, so the merged build remains
the original fork's records substrate (agent workspaces,
sessions, executions, library sources, digest-only searches,
documents, usage, exports), unchanged in code, and the
newcomers' engines are registered as gaps. Where their activity
would be recorded by an embedding organization, it takes the
core's existing forms: documents as metadata + checksums,
searches as digests, usage as quantities — content, queries, and
signatures themselves are never held. The tier baseline is the
Moderate / L2 baseline, inherited in full; the caveat of
`UNION-SPEC.md` stands (a planning equivalence, never a
credential claim).

## 7. Verification record

- Extractor: taxonomy-copy assertion against the original
  `scratch/extract.py` passed before tagging; census citations
  **9 / 9 verbatim** against the cached descriptions.
- Specs: `specs/specs.json` 1 → 7 sheets; the original sheet is
  **deep-equal to git HEAD** after the append (the file
  re-serializes identically under the original `indent=1`
  settings).
- Tests: **94 → 106, all passing** — `tests/test_additions.py`
  (12 tests): spec integrity (membership and order, the
  zero-claim table, pattern absence from the texts, census
  citations pinned, sheet schema and tier) and one substrate
  case per newcomer plus an additions export-checksum case.
- Negative control: the core is unchanged, so the group's
  signature drill was re-run in this tree — `_check_sandbox_unused`
  patched to a no-op in the real store → **106 ran, exactly 5
  failed**: the original drill's 4 single-use-dependent tests
  plus the additions module's RelativityOne sandbox case. Store
  restored from `tests/store.py.premutation` and verified
  **SHA-256-identical** (`7030f9fd…`, the shipped hash); suite
  green again. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`. (A first patch attempt
  produced a syntactically invalid store — a closing parenthesis
  dropped from the replaced body — and its run was discarded;
  the drill was re-done with the seam body replaced verbatim and
  the mutant source syntax-checked before running.)
- `src/` is byte-identical to the shipped build: no source file
  differs from git HEAD (store hash above; the group diff is
  `specs/specs.json`, the two READMEs, `ADDENDUM.md`, and
  `tests/test_additions.py` only).
