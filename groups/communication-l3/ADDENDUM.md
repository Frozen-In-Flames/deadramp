# Addendum — Communication, CMMC L3-adjacent (FedRAMP High): the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:communication-l3`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its
12-function core, and its High control baseline are **unchanged**.
This document records what joined, what the newcomer claims under
the group's existing taxonomy, the core-delta decision, and the
updated union statement.

**Headline: fork spec'd 1 / 1; 1 new claim; core delta — zero
functions extended, `src/` byte-identical; tests 138 → 149, all
passing.** The newcomer is the category's flagship team-messaging
suite, and it files at High with exactly **one** of the taxonomy's
21 families tagged — the floor effect the union spec recorded for
this tier, at its extreme. **2 new gap functions** are named in
§5; one already-registered gap gains a by-substance member, and
the secure-transmission gap explicitly gains **no** claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2230252267` | Slack Technologies / GovSlack |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the original `scratch/extract.py`'s taxonomy via
  `ast` (parsed, never executed) and asserts its literal copy of
  the (id, label, regex) triples equal to the original's before
  tagging** — the taxonomy was applied verbatim, including its
  five documented wording-artifact corrections, not re-tuned for
  the newcomer. Same sentence splitting, same evidence rule
  (first matching sentence per family, stored verbatim, 400-char
  truncation), same sheet schema. As a second verbatim proof, the
  extractor **reproduces the original 6 forks' shipped claim
  tables exactly** from the raw cache (ids + evidence, fork by
  fork) before tagging anyone new.
- The sheet is **appended** to `specs/specs.json` after the
  original 6, which are byte-for-byte untouched (pure 24-line
  insertion; the originals verified deep-equal against git HEAD
  and byte-preserved through the sixth sheet's closing brace).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The sheet's
  description is byte-equal to the census copy in
  `../../remainder/uncovered.json`.
- The census starting point was verified, not trusted: both
  **census citations** for this fork (from
  `../../remainder/class_all.json`) were re-checked against the
  cached description and **2 / 2 verify** as verbatim substrings.
- **No exclusion trap applies.** The record's
  `certified_services` field is empty and no hosted-catalogue or
  "not authorized" segment exists in the description (asserted in
  the extractor). Only `service_desc` was matched, per house
  method.
- The fork is FedRAMP **High** (Certified, SaaS, Public Cloud),
  so the group stays single-tier and the High baseline is
  inherited in full (Merge Rules 1–2), unchanged.

## 2. What the addition claims

**1 claim.** The newcomer's whole description is 704 characters
of consumer-product marketing prose; five of its six sentences
tag nothing.

| Function | Additions claiming | Group total (7) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Messaging (email & messaging channels) | 1 | 2 | **Core** — composition + delivery records |
| Identity proofing, login & access control | 0 | 2 | Core (RBAC, uplifted); identity products Extended |
| Workflow & business process automation | 0 | 2 | Extended — engines |
| Secure & encrypted transmission | 0 | 2 | Extended — E2E transport |
| Key & certificate lifecycle management | 0 | 1 | Extended — CA automation |
| Notifications, alerting & critical-event communications | 0 | 1 | **Core** — templates, dispatch, scheduling |
| Reporting, dashboards & analytics | 0 | 1 | Core (substrate); engines Extended |
| Voice, telephony, IVR & contact center | 0 | 1 | Extended — media + conversation engines |
| All other 13 families | 0 | 0 | As UNION-SPEC (carried substrate / Extended / named absences) |

The claim, with its evidence (the description's third sentence,
also census citation #2):

- **`messaging`** — "It's the leading channels-based messaging
  platform, used by millions to align their teams, unify their
  systems, and drive their business forward." Substantive, not an
  artifact: messaging is the offering's stated primary function.

### Near-misses, itemized per sentence

The full per-sentence map is
`scratch/additions_sentence_map.json`:

- **S1** ("GovSlack is an instance of Slack created specifically
  for the purposes of handling high workloads for Government
  customers and highly regulated commercial sectors.") —
  instantiation and boundary prose; tags nothing. "customers" is
  not `contacts_directory`'s "contacts".
- **S2** ("Slack has transformed business communication.") —
  census citation #1: it verifies as text and tags **nothing**.
  "communication" (singular) is not a token in any pattern, and
  `secure_transmission` requires the contiguous phrase "secure
  communications". Verification is not a claim, stated plainly.
- **S3** (the claim sentence) — also carries "align their teams,
  unify their systems": team-collaboration substance with **no
  family in this taxonomy** (`workspaces` is a Collaboration-
  taxonomy family, not one of Communication's 21). On
  "channels-based", see the wording note below.
- **S4** ("Only Slack offers a secure, enterprise-grade
  environment that can scale with the largest companies in the
  world.") — `secure_transmission` near-miss: "secure," modifies
  "enterprise-grade environment"; there is no contiguous
  secure transmission/message/messaging/communications phrase,
  and **"encrypt" appears nowhere in the description**. The
  secure-transmission gap gains no claimant (§5).
- **S5** ("…connect all their other software tools and services,
  and find information they need to do their best work.") — two
  by-substance surfaces, neither a claim: "find information" is
  search substance without the literal "search" token
  `search_ediscovery` requires; "connect all their other software
  tools and services" is integration substance, and **this
  taxonomy has no integrations family at all** (named as a new
  gap in §5).
- **S6** ("Slack is where work happens.") — slogan; tags nothing.

### Checked absences (tokens verified absent from the description)

No **video**, **voice** / call / telephony, **audit**, login /
authentication / permissions, retention / archive, analytics /
dashboard, workflow / automat-, contacts / directory, schedul-,
signature, or payment tokens — and no **"email"** token either:
the messaging claim rests on "messaging" alone. The consequence
is stated plainly: the union spec's standing named absence —
**video conferencing / real-time media transport, claimed by 0
siblings** — *survives* the addition of the market's flagship
messaging suite, because its High listing never mentions media,
calls, or video. Nobody believes the product lacks calls; the
listing does not say them, and the taxonomy reads listings.

### Wording note (recorded, not an artifact in the claim)

"Channels" names different things on the two sides of this spec.
In the fork's description, channels are **persistent team rooms**
— the product's organizing unit. In this build, **channels**
(Core 2) are *delivery channel kinds* (email / sms / voice /
push) whose configuration gates dispatch. The `messaging` claim
is unaffected — composition and delivery records are its records
form either way — but the persistent-room surface itself is not
part of this union and is named as a gap in §5, with the boundary
noted there.

## 3. Core-delta decision

| Claimed family (addition) | Disposition | Core delta |
|---|---|---|
| Messaging (1) | Core 4 (composition), Core 5 (delivery records), Core 6 (dispatch & receipts), Core 8 (acknowledgement tracking) | **Carried** — no change |

**Result: the core is unchanged.** The one function the newcomer
claims presupposes only records forms the build already has:
messages composed to contacts and groups, one delivery record
per recipient × channel kind, dispatch through the reference
transport (receipts labelled `reference_transport: true` — the
build transmits nothing over any real network, and no real-time
messaging transport is claimed for it), and acknowledgement
tracking. Message and delivery records hold recipients,
addresses, subjects, and delivery metadata; the category
discipline stands that records are the substrate's own record of
what was composed and dispatched — no third-party message
contents are ingested or stored by the addition. `src/` is
byte-identical to the shipped build (`src/comm/store.py` SHA-256
`bfc7877c7a38dae178850b07cccbb1df67efb1ef78e5bdad054be1139125f45d`
before and after this addendum's work, the mutation drill
included; all eight module hashes were recorded at the start of
the build and re-verified at the end). The tier baseline does
not change: same tier by construction. High-tier features
(hash-chained audit, fail-closed writes, audit query,
`/audit/verify`, AC-7 lockout, the AC-5 auditor role) are exactly
as shipped and are exercised against the newcomer's flow by the
additions tests.

## 4. Updated union statement

The group now covers **7 forks** (6 original siblings + 1
remainder addition), **12 claims** in total (11 + 1), with **6 of
7** forks carrying at least one claim (Akamai Cloud's zero-claim
sheet stands). The merged build remains the same 12-function
communications substrate at the High baseline — directory,
channels, templates, composition, delivery records, dispatch &
receipts, scheduling, acknowledgement tracking, records & search,
REST API, RBAC with the auditor role, hash-chained fail-closed
audit — now spec'd against 7 marketplace offerings instead of 6.
The group's character sharpens rather than changes: at High,
"communication" predominantly meant a governed transmission
enclave; the addition is the tier's flagship *team-messaging*
suite, and even it arrives as boundary-adjacent marketing prose
tagging a single family. The spec's floor finding is therefore
restated with the addition included: claim counts at this tier
measure listing style at least as much as product surface.

## 5. Gaps — for the registry at ship

**New gap functions** (2), both from the newcomer's own
description, neither rounded into a claim:

- **App integration & connector platform** (the surface that
  connects third-party software tools and services into the
  messaging environment) — GovSlack, from "connect all their
  other software tools and services". This taxonomy has no
  integrations family; the function is asserted in substance
  only.
- **Persistent channel / workspace collaboration surface**
  (channels as persistent team rooms — membership, threads,
  shared workspace) — GovSlack ("channels-based messaging
  platform", "Slack is where work happens"). Distinct from Core
  2's delivery-channel configuration records. Boundary note: the
  workspace substrate proper is built in the Collaboration
  groups; this gap is named here because the fork's own
  description centers on it, so the final batch can place it
  deliberately rather than by default.

**Existing gaps gaining members:**

- **Search & eDiscovery engines** — +1 **by substance**:
  GovSlack ("find information they need to do their best work").
  The `search_ediscovery` family claim itself did not fire (no
  "search" token); Core 9's literal search over the substrate's
  own records is unchanged, and the Extended remainder (corpus
  search / eDiscovery production) gains the member.

**Existing gaps explicitly gaining no claimant:**

- **Secure & encrypted transmission** — GovSlack's S4 is
  platform prose ("a secure, enterprise-grade environment") with
  no contiguous secure-transmission phrase and no "encrypt"
  token. Recorded so the gap's claimant count is not rounded up
  at the final batch.
- **Workflow / BPM engines** — no workflow or automation token
  appears in the description.
- **Video conferencing / real-time media** — remains a named
  absence at **0 of 7** (§2).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, registry fields as
  published, the literal claim table, the 20-family zero-claim
  set, group totals (7 forks / 12 claims / 6 claiming), verbatim
  evidence, the census citations, and the near-miss token pins
  (see `tests/test_additions.py`).
- The newcomer's claimed shape is exercised against the
  substrate in the same tests: a message addressed to the team
  group composed, dispatched via the reference transport with a
  labelled receipt, and acknowledged (GovSlack's channels-shaped
  addressing run through Core 4/5/6/8); dispatch with no enabled
  channel failing with `no_enabled_channel`; and the High
  baseline intact around the flow (audit chain verifies after
  the compose; the auditor holds no compose permission).
- **Tests: 138 → 149, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill — Drill 1, the send gate, carried from Group
  11 — was re-run in this tree: the send-gate line in
  `CommStore._dispatch_deliveries` (`if channel is None:`, the
  exact line the shipped drill record names) was patched to
  `if False:` and the full suite ran — **149 tests, exactly 5
  failures**: the shipped drill's 4 (the two dispatch
  channel-gate tests and the two negative-control canonical
  cases) plus exactly 1 from the new additions module (the
  GovSlack no-enabled-channel case), tripping exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`. Drill 2 (the audit-hash
  drill) was not re-run: the addition changes no audit code and
  no audit-facing behavior, and its record stands as shipped.
