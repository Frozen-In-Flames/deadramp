# Addendum — Collaboration, CMMC L3-adjacent: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:collaboration-l3`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 11-function
core, its High control baseline, and its tier uplifts are
**unchanged**. This document records what joined, what the newcomer
claims under the group's existing taxonomy, the core-delta decision
for the claimed function, and the updated union statement.

**Headline: forks spec'd 1 / 1; 1 new claim; core delta — zero
functions extended, `src/` byte-identical; tests 239 → 251, all
passing.** The newcomer is Microsoft 365 Government Community Cloud
— the category's flagship suite — and its High listing is the
clearest instance yet of the floor effect UNION-SPEC.md already
names for this group: a boundary/enclave description that tags
exactly **one** function. The census classified it into
Collaboration on its first sentence ("a suite of cloud-hosted
messaging and collaboration services"), and the taxonomy tags that
same sentence for messaging — and nothing else in the description.
**1 new gap function** is named in §5; no existing gap gains a
claimant.

## 1. Membership and method

The 1 fork (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `MSO365MTA` | Microsoft / Microsoft 365 Government Community Cloud & Supporting Services |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **AST-parses the original `scratch/extract.py`'s taxonomy
  (parsed, never executed — executing it would regenerate
  `specs.json`) and asserts its literal copy of the (id, label,
  regex) triples equal to the original's before tagging** — the
  taxonomy was applied verbatim, not re-tuned for the newcomer.
  Same sentence splitting, same evidence rule (first matching
  sentence per family, stored verbatim, 400-char cap), same sheet
  schema and key order. The sheet is **appended** to
  `specs/specs.json` after the original 17, which are byte-for-byte
  untouched (the re-serialized file is byte-identical to HEAD
  through the 17th sheet's closing brace, and the original entries
  are deep-equal to git HEAD after the append; verified in the
  build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **High** (authorization status *FedRAMP In Process*), so the
  group stays single-tier and the High baseline — hash-chained
  audit, fail-closed writes, audit query, logon lockout, auditor
  role — is inherited in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: the fork's
  **1 census citation** was re-checked against its own cached
  description and **verifies** as a verbatim substring. It is the
  description's first sentence — the same sentence the messaging
  claim rests on (§2).
- **No exclusion trap applies to the newcomer.** The record's
  `certified_services` field is empty (asserted in the extractor),
  so there is no hosted-services block to exclude; only
  `service_desc` was matched, per house method.
- Registry fields are recorded as the source publishes them: the
  record's `service_model` is an **empty list** (the source
  publishes none for this record; the sheet does not invent "SaaS"
  from the product's reputation), and its `deployment_model` is
  **"Public Cloud"** verbatim — despite the product name's
  "Government Community Cloud". Both are pinned by test.

## 2. What the addition claims

**1 claim.** The fork carries the group's taxonomy as follows,
with the combined count (original 17 + addition = 18 forks)
alongside:

| Function | Addition claiming | Group total (18) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Messaging & chat | 1 | 2 | **Core** |
| All other 20 families | 0 | — | unchanged |

Per-fork claim count: Microsoft 365 GCC **1**. The full claim
table is pinned literally in `tests/test_additions.py`
(`EXPECTED_CLAIMS`), as is the set of 20 families the addition does
not claim.

The one claim is **substantive, not a wording artifact**: the
evidence sentence names messaging as one of the suite's two stated
primary services. There is no artifact-weight discount to record
for it. It is also the group's second messaging claim — UNION-SPEC
recorded messaging at 1 of 17 (6%) at High against 19% at Moderate,
the steepest feature-family collapse in the cross-tier comparison;
the flagship suite's own listing is why: it enumerates no features
at all beyond that first sentence.

### Near-misses, itemized

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`; the description is 7
sentences):

- **Sentence 1** (the claim sentence) — "messaging and
  **collaboration services**" is not `workspaces`: the family
  requires collaborat* followed by platform / tools / environment
  / space / solution / suite, or "collaboration" followed by the
  same nouns; "services" is not among them. The census classified
  the fork as Collaboration on this sentence's plain meaning; the
  taxonomy tags only its messaging half. Recorded, not tuned.
- **Sentence 2** — "streamlined **communication**" is not
  `voice_contact` (the family requires "voice communication",
  "unified communications", telephony, and kin — bare
  "communication" is not enough). "Comprehensive **security**"
  matches no family: no access-control phrase (no SSO, RBAC,
  authentication, or identity wording) and "encrypt" never appears
  anywhere in the description, so neither `access_control` nor
  `encryption` fires — the same shape as Webex's security prose in
  the L2 additions. "Simplified information technology (IT)
  **management**" is not `task_work` ("service management" is the
  family's phrase; "IT management" is not), and no
  administration-console family exists in this taxonomy; unlike
  Webex's Control Hub sentence in the L2 group, this is a benefit
  adjective ("simplified"), not a named console surface, so it is
  recorded here as a near-miss and **not** registered as a gap.
- **Sentence 3** — "the **interactivity** of on-premises client
  and server applications" is not `api_integration` (the family's
  stem is `integrat\w+`; "interactivity" does not contain it) and
  "web-based services" is not `knowledge` ("web content" is the
  family's phrase). Platform prose about delivery shape.
- **Sentences 4–6** — the Azure Government passage ("leverages
  Azure Government as the IaaS/PaaS", "relies on Azure
  Government-inherited services", "refer to the Azure Government
  ATO package") is the platform layer the fork sits on, stated in
  its own listing. Two pattern notes: `\bai\b` does **not** fire
  on "IaaS/PaaS" (word boundary), so no `ai_assistance` claim; and
  "ATO package" contains no "audit" token, so no `audit` claim.
  The inherited-services dependency is recorded as a platform note
  in §5, not a function.
- **Sentence 7** — "**collaborative continuous monitoring** with
  Microsoft" tags nothing: this taxonomy has no monitoring family,
  and "collaborative" is followed by "continuous", not a
  workspaces noun. It is the fork's one named surface with no
  family at all — registered as a new gap in §5, not rounded into
  a claim.

## 3. Core-delta decisions

The one claimed family already has a disposition in UNION-SPEC:

| Claimed family (addition) | Disposition | Core delta |
|---|---|---|
| Messaging & chat (1) | Core 2 — channels, threaded messages, mentions → notifications | **Carried** — no change |

**Result: the core is unchanged.** The claim presupposes no
records form the build lacks, and the High-baseline uplifts
(hash-chained audit, fail-closed writes, audit query/reduction,
logon lockout, auditor role) are untouched. `src/` is
byte-identical to the shipped build (all 7 source files verified
against the pre-addition hash list after all work, the mutation
drill included; `src/collab/store.py` SHA-256
`bd8941693f91df9705340102a0932f17463583dfaba785ae9222528b79aa880c`,
the shipped hash). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **18 forks** (17 original siblings + 1
remainder addition), **50 claims** in total (49 + 1), with **14 of
18** forks carrying at least one claim — the zero-claim set is
unchanged at 4. The merged build remains the same 11-function
collaboration substrate at the High baseline — workspaces,
messaging, file records, calendaring, presence, boards, literal
search, notifications, REST API, RBAC with the auditor role,
hash-chained fail-closed audit — now spec'd against 18
marketplace offerings instead of 17. The addition's character: the
marketplace's flagship collaboration suite files at High as an
enclave description, claims the substrate's messaging function in
its opening sentence, and otherwise describes its boundary, its
underlying platform, and one agency-facing monitoring arrangement.
UNION-SPEC's reading of this group — at High, "collaboration"
predominantly means a governed enclave in which collaboration
happens, described by its boundary — now holds for the category's
best-known product as well.

## 5. Gaps — for the registry at ship

**New gap functions** (1):

- **Collaborative continuous monitoring service** — the
  agency–vendor continuous-monitoring arrangement the fork's
  listing closes with ("Federal agencies interested in
  collaborative continuous monitoring with Microsoft should reach
  out to: …"); a named surface in the fork's own description with
  no family in the collaboration taxonomy (this build's audit
  trail is the substrate such an arrangement reports from, not
  the arrangement itself)

**Existing gaps gaining claimants:** none. The addition's single
claim is a Core function (messaging), and none of the 9 Extended
functions in UNION-SPEC gains a claimant — meetings, voice, AI
assistance, records & governance beyond the seed, workflow
engines, task management, learning, knowledge, and e-signature all
stand at their original counts. The 5 baseline gaps named at High
(IA-2(1)/(2) & IA-5 IdP properties, SC-13 FIPS-validated crypto,
SC-28 encryption at rest, AU-11 audit retention, AC-11/AC-12
session lock/termination) are likewise unchanged.

**Platform note (not a gap):** the fork is a tenant of an
underlying government cloud platform — it "leverages Azure
Government as the IaaS/PaaS" and "relies on Azure
Government-inherited services", pointing readers at that
platform's ATO package. Inherited-services dependency is a
platform posture of the fork, recorded here; this build is the
collaboration substrate, not that platform, and claims nothing
about it.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal claim table,
  the 20-family unclaimed set, verbatim evidence, description
  equal to the cached source, the census citation (which is also
  the claim's evidence), the near-miss pins, and the
  source-as-published registry fields (see
  `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests, at the High baseline: a channel message with a
  member mention notification, a versioned file record whose list
  view carries no content (opaque-reference discipline), and the
  hash-chained audit trail verifying end to end with an
  actor/action reduction query over the fork's activity.
- **Tests: 239 → 251, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the membership
  condition in `CollabStore._require_workspace_access`
  (`src/collab/store.py`) was patched to `if False:` — the exact
  mutant of the shipped Drill A — and the full suite ran — **251
  tests, 15 failures**: the shipped drill's 14 plus 1 from the new
  additions module (the M365 membership-boundary post case),
  which trips on the mutant exactly as designed. `store.py` was
  restored from the pre-mutation copy and verified SHA-256-
  identical to the shipped hash (`bd894169…`); the whole `src/`
  tree was re-verified against the pre-addition hash list and the
  suite re-ran green. Recorded in `tests/README.md`; raw output
  in `scratch/additions_mutation_run.txt`.
