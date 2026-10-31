# Addendum — Collaboration, CMMC L2: the 3 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 3
previously uncategorized forks of remainder build unit
**`addition:collaboration-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 11-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomers claim under the group's
existing taxonomy, the core-delta decision for every claimed
function, and the updated union statement.

**Headline: forks spec'd 3 / 3; 11 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 192 → 208, all
passing.** One of the three is a **zero-claim fork** (IdeaScale Gov):
both of its census citations verify as verbatim description text
yet tag no family, and its entire described function — innovation
management & crowdsourcing — has no family in the group's taxonomy;
it is registered as a new gap in §5, not rounded into a claim.
**5 new gap functions** are named in §5, and 6 already-registered
gaps gain claimants (one of them by substance only).

## 1. Membership and method

The 3 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1511207635` | Cisco Systems Inc. / Webex for Government |
| 2 | `F1408115175` | Huddle US / Huddle Enterprise Cloud Content Collaboration and File Sharing Portal for Government |
| 3 | `F1512017638` | IdeaScale / IdeaScale Gov |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **AST-parses the original `scratch/extract.py`'s taxonomy
  (parsed, never executed — executing it would regenerate
  `specs.json`) and asserts its literal copy of the (id, label,
  regex) triples equal to the original's before tagging** — the
  taxonomy was applied verbatim, not re-tuned for the newcomers.
  Same sentence splitting, same evidence rule (first matching
  sentence per family, stored verbatim, 400-char cap), same sheet
  schema and key order. The 3 sheets are **appended** to
  `specs/specs.json` after the original 57, which are byte-for-byte
  untouched (the re-serialized file is byte-identical to HEAD
  through the 57th sheet's closing brace, and the original entries
  are deep-equal to git HEAD after the append; verified in the
  build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 3
  descriptions were present; no live fetching. All 3 are FedRAMP
  **Moderate** and FedRAMP Certified, so the group stays
  single-tier and the L2 baseline is inherited in full (Merge
  Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **4
  census citations** for these forks (Webex 1, Huddle 1, IdeaScale
  2) were re-checked against the forks' own cached descriptions
  and **4 / 4 verify** as verbatim substrings.
- **No exclusion trap applies to the newcomers.** None of the 3
  records carries a hosted-services block: every record's
  `certified_services` field is empty (asserted in the extractor).
  Only `service_desc` was matched, per house method.

## 2. What the additions claim

**11 claims** across the 3 forks; 2 of 3 carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 57 + additions = 60 forks) alongside:

| Function | Additions claiming | Group total (60) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| APIs, integrations & interoperability | 1 | 32 | **Core** — the service is a REST API |
| Workflow & process automation | 1 | 26 | Extended — domain process engines |
| AI assistance, speech & analytics | 1 | 22 | Extended |
| Messaging & chat | 1 | 12 | **Core** |
| Audit logging & trails | 1 | 12 | **Core** — append-only audit |
| Shared workspaces & team collaboration | 2 | 12 | **Core** |
| Voice, telephony & contact center | 1 | 10 | Extended — real-time media transport |
| File sharing, storage & content management | 1 | 10 | **Core** — versioned file records |
| Records, governance & compliance management | 1 | 10 | Extended — beyond the versioning/audit seed |
| Meetings, video & web conferencing | 1 | 6 | Extended — media transport |
| All other 11 families | 0 | — | unchanged |

Per-fork claim counts: Webex for Government **7**, Huddle **4**,
IdeaScale Gov **0**. The full per-fork table is pinned literally in
`tests/test_additions.py` (`EXPECTED_CLAIMS`), as is the set of 11
families no addition claims.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no pattern
(the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Webex for Government** — The Calling bullet ("a proven cloud
  calling solution … replace your on-premises PBX network") matches
  no `voice_contact` alternative: "calling" alone is not "call
  routing / call recording / unified communications / telephony".
  The voice claim rests on the next sentence ("voice queues and
  call routing") and on the UCM Cloud sentence ("unified
  communications"). The Virtual Visitation bullet's "advanced
  scheduling portal" is not `calendaring`: the family requires
  "scheduling (solution|system|platform)", "scheduler", or
  scheduling *of* meetings/resources/events — "portal" is not in
  the list, so a genuine scheduling surface earns no calendaring
  claim (the portal itself is a new gap, §5). The Control Hub
  bullet ("a centralized and comprehensive administrative portal
  for all your collaboration services") matches no family — no
  administration-console family exists (new gap, §5). And for all
  its "secure" prose, the description never writes "encrypt" (no
  `encryption` claim) and never uses an access-control phrase —
  no SSO, RBAC, authentication, or identity wording (no
  `access_control` claim).
- **Huddle** — "Fully auditable workspaces with trackable tasks
  and assignments" is not `task_work`: the family requires "task
  tracking", and the reversed wording does not fire (the substance
  enlarges the task gap by substance, §5). "Total control over who
  can access, view, and edit workspaces and documents" is not
  `access_control`: the literal phrase "access control" is never
  written and none of the family's enumerated alternatives
  appears. **File sharing exists only in the product's name** —
  the description says "documents" and "workspaces" but never a
  file-sharing / document-management phrase, so no `file_sharing`
  claim (the name-only precedent: product names are not claims).
  "Zero-trust architecture" and "stringent security and risk
  mitigation strategies" match no family; platform prose.
- **IdeaScale Gov** — the whole description is two sentences, and
  neither tags anything. "…collaboratively transform that input
  into actionable project plans" is not `workspaces` (the family
  needs collaborat* followed by platform/tools/environment/space/
  solution/suite; here it is followed by "transform") and not
  `task_work` ("project plans" is not "project management").
  "Make the most of the collective knowledge of their numbers" is
  not `knowledge` ("collective knowledge" is not "knowledge
  management / knowledge base"). "Innovation management" and
  "crowdsourcing" — the fork's entire function — have **no family
  at all** in the taxonomy. Both census citations for this fork
  sit inside these two sentences: they verify verbatim and tag
  nothing. Verification is not a claim.

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the group's
law, applied verbatim:

- **Webex, `workflow`** fires via the family's bare `workflow`
  alternative on "Webex for Government Meetings simplifies your
  company's workflows at scale" — a prose use of the word, not a
  process-automation statement. The claim stands; the family's
  Extended disposition (domain process engines) does not depend on
  it, and §5 counts the enlargement at this weight.
- **Webex, `meetings_video`** evidence is the same Meetings
  sentence, firing on the bare `meetings` alternative; the
  family's substantive sentences in this description are the
  Messaging bullet ("in between meetings") and the Webinars
  bullet ("host webinars"). First-match evidence is the house
  rule; the artifact is recorded, not re-anchored.
- **Webex, `ai_assistance`** fires via the bare `\bai\b`
  alternative on "optimizing collaboration through AI-enabled
  software and hardware" — a sentence as much about devices as
  about software assistance.
- **Huddle, `api_integration`** fires via the family's `integrat`
  stem on the adjective use "tightly integrated workspaces"; the
  substantive integration sentence is the later "Integrations with
  Microsoft Office ensure a seamless experience". The stored
  evidence is the first match, per house method, and the artifact
  is pinned by test.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Messaging & chat (1) | Core 2 — channels, threaded messages, mentions | **Carried** — no change |
| File sharing (1) | Core 3 — versioned file records (metadata + SHA-256; contents stay behind `get_file`, list views carry no content) | **Carried** |
| Shared workspaces (2) | Core 1 — workspace registry, membership boundary | **Carried** |
| APIs & integrations (1) | Core 9 — the service is a REST API | **Carried** — product-specific connector engines are a new gap (§5) |
| Audit logging & trails (1) | Core 11 — append-only audit | **Carried** |
| Meetings, video & web conferencing (1) | Extended — media transport; the coordination surface (calendaring, channels, presence) is already Core | **Carried** — gap gains a claimant (§5) |
| Voice, telephony & contact center (1) | Extended — real-time media transport | **Carried** — gap gains a claimant (§5) |
| Workflow & process automation (1) | Extended — domain process engines on top of the substrate | **Carried** — gap gains a claimant at artifact weight (§5) |
| AI assistance, speech & analytics (1) | Extended — search in Core stays literal substring matching, stated plainly | **Carried** — gap gains a claimant at artifact weight (§5) |
| Records, governance & compliance (1) | Extended beyond the seed — the seed itself (file versioning, audit trail) is Core 3/11 and Huddle's "fully auditable workspaces" runs on it | **Carried** — gap gains a claimant (§5) |

**Result: the core is unchanged.** No function the 3 claim
presupposes a records form the build lacks, and the two Extended
media families gain claimants without changing their disposition.
`src/` is byte-identical to the shipped build (`src/collab/store.py`
SHA-256
`d2b943e29a592c3f9b007e2cc6ca399e90b6127a446b9380e927f1c3b01f577a`
before and after this addendum's work, the mutation drill included;
all 7 source files hash-identical, verified by before/after hash
lists in scratch). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **60 forks** (57 original siblings + 3
remainder additions), **233 claims** in total (222 + 11), with
**53 of 60** forks carrying at least one claim — the zero-claim set
grows from 6 to 7 with IdeaScale. The merged build remains the same
11-function collaboration substrate — workspaces, messaging, file
records, calendaring, presence, boards, literal search,
notifications, REST API, RBAC, append-only audit — now spec'd
against 60 marketplace offerings instead of 57. The additions'
character: Webex is a flagship unified-communications suite whose
claims straddle the Core (messaging, files, workspaces) and the
Extended media families (meetings, voice); Huddle is a
workspaces-and-governance sibling whose audit claim runs on the
Core seed; IdeaScale is the group's clearest case of a fork whose
function sits entirely outside the category taxonomy, joining the
zero-claim set with its function named as a gap rather than forced
into a family.

## 5. Gaps — for the registry at ship

**New gap functions** (5):

- **Innovation management & crowdsourcing platform** — IdeaScale
  Gov's entire described function (stakeholder input solicitation,
  crowdsourced idea development, transformation of input into
  project plans); no taxonomy family exists for it and the fork
  claims zero families
- **Centralized administration console for collaboration
  services** — Webex Control Hub ("a centralized and comprehensive
  administrative portal for all your collaboration services")
- **Virtual visitation scheduling portal** — business-rules and
  workflow configuration, zero-touch device connectivity within
  meetings (Webex Virtual Visitation Service)
- **Collaboration hardware endpoints & purpose-built devices** —
  Webex (collaboration devices "purpose-built for your diverse
  needs and spaces"; AI-enabled hardware); platform layer
- **Product-specific connector engines** — Huddle (Microsoft
  Office integrations); Core 9 is the API surface, the connectors
  into named third-party products are engines on top of it (the
  Group 33 connector-gap precedent)

**Existing gaps gaining claimants** (all registered under Group 2
in GAPS.md):

- **Meetings / video media transport** — +1: Webex (Meetings and
  Webinars claims)
- **Voice / telephony / contact center** — +1: Webex (Calling,
  voice queues and call routing, UCM Cloud unified communications)
- **Workflow / process-automation engines** — +1: Webex, at
  artifact weight (the claim fired on "workflows at scale" prose;
  recorded in §2)
- **AI assistance, speech, and analytics** — +1: Webex, at artifact
  weight ("AI-enabled software and hardware"; recorded in §2)
- **Records & governance beyond the versioning/audit seed** — +1:
  Huddle ("fully auditable … for data governance and compliance")
- **Task & project management beyond board cards** — +1 **by
  substance**: Huddle ("trackable tasks and assignments"); the
  `task_work` family claim itself did not fire on the reversed
  wording, recorded in §2

**Explicitly gaining no claimant:** the encryption platform note —
none of the 3 descriptions uses "encrypt" (Webex's security prose
notwithstanding), and the platform layer is unchanged.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the additions' unclaimed-family set, verbatim evidence,
  descriptions equal to the cached source, the census citations,
  and the near-miss / wording-artifact pins (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: a channel message with a member mention
  notification, a versioned file record whose list view carries
  no content, and a calendared meeting event (Webex); file
  versioning v1→v2 with audit entries and literal search (Huddle);
  a workspace board of positioned text cards with an outsider's
  read denied — the substrate minimum, no Core slice attributed
  (IdeaScale).
- **Tests: 192 → 208, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the membership
  condition in `CollabStore._require_workspace_access`
  (`src/collab/store.py`) was patched to `if False:` — the exact
  mutant of the shipped drill — and the full suite ran — **208
  tests, 16 failures**: the original drill's 14 (negative control
  ×4, workspaces ×2, messaging ×2, boards ×2, files, calendar,
  search, service) plus 2 from the new additions module (the Webex
  membership-boundary post case and the IdeaScale outsider-read
  case), which trip on the mutant exactly as designed.
  `store.py` was restored from the pre-mutation copy and verified
  SHA-256-identical to the shipped hash; the suite re-ran green.
  Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
