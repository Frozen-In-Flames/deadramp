# Addendum — Communication, CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:communication-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 12-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomer claims under the group's
existing taxonomy, the core-delta decision, and the updated union
statement.

**Headline: fork spec'd 1 / 1; 1 new claim; core delta — zero
functions extended, `src/` byte-identical; tests 82 → 92, all
passing.** The newcomer is the group's canonical citizen-
communications platform by reputation and its thinnest description
by text: three sentences of marketing prose, of which exactly one
tags a family. **1 new gap function** is named in §5, and no
already-registered gap gains a claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1311252652` | Granicus / GovDelivery Communications Cloud |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact (id, label, regex) triples** —
  the taxonomy was applied verbatim, not re-tuned for the newcomer.
  Same sentence splitting, same evidence rule (first matching
  sentence per family, stored verbatim), same sheet schema. The
  sheet is **appended** to `specs/specs.json` after the original
  10, which are byte-for-byte untouched (the file re-serializes
  identically for the original entries and is byte-preserved
  through the tenth sheet's closing brace; asserted in the
  extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **Moderate / Certified** (SaaS, Government Community Cloud), so
  the group stays single-tier and the L2 baseline is inherited in
  full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: both
  **census citations** for this fork were re-checked against the
  fork's own cached description and **2 / 2 verify** as verbatim
  substrings — with the twist recorded in §2: neither citation
  tags a family.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty and no scope-exclusion
  segment exists in its description (asserted in the extractor).
  Only `service_desc` was matched, per house method.

## 2. What the addition claims

**1 claim.** The fork's description is three sentences long; the
per-sentence map is `scratch/additions_sentence_map.json`.

| Function | Additions claiming | Group total (11) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Messaging (email & messaging channels) | 1 | 9 | **Core** — composition + delivery records |

The claim's evidence is the description's third sentence: "The
Advanced Package for Communications Cloud and the Targeted
Messaging Service are feature offerings available with Granicus'
GovDelivery Communications Cloud." — `messaging` fires on
"Messaging". The group's "no fork has zero claims" floor (stated
in UNION-SPEC) survives the addition: the newcomer claims exactly
one family, and 11 of 11 forks now carry at least one claim.

**The census-citation twist, stated plainly.** Both census
citations verify as verbatim description text, and **neither tags
a family**: they are the description's first two sentences, which
match nothing. The single claim rests on the third sentence,
which the census did not cite. Verification is not a claim, in
both directions.

### Near-misses, itemized per sentence

- **Sentence 1** ("More than 1,000 public sector organizations use
  Granicus' highly secure cloud communications solutions … to
  enhance the citizen experience for greater than 150 million
  people.") — "highly secure cloud communications" is not
  `secure_transmission`: the family requires "secure" immediately
  followed by transmission / message / messaging / communications,
  and "cloud" intervenes. "citizen experience" matches no family
  (there is no citizen-engagement family; `contacts_directory`
  requires contacts / constituent / CRM / directory phrasing).
  The reach figures tag nothing.
- **Sentence 2** ("As the only FedRAMP-authorized marketing
  automation platform … is the most secure marketing solution
  available …") — "marketing automation" is not
  `workflow_automation`: the family requires `automat\w+` followed
  by the / of / issuance / business, and "automation platform"
  has none of them. This is the fork's headline function and it
  has no family — it becomes the gap in §5. "most secure marketing
  solution" repeats the `secure_transmission` adjacency miss.
  "serves federal, state, and local government customers" is not
  `contacts_directory` ("customers" is none of the family's
  tokens). "FedRAMP-authorized" is program-status prose and tags
  nothing.
- **Sentence 3** (the claim sentence) — beyond the `messaging`
  hit: "Targeted" asserts audience targeting, which has no
  family (the targeting engine is the §5 gap, not a claim), and
  the "Advanced Package" is a packaging name, not a function.
- **Whole-description absences** — `ai_ml` does not fire
  ("automation" is not "autonomous"; no standalone "AI" token);
  `notifications_alerts` does not fire — the description contains
  no notification token at all, which is recorded as a finding
  about the *description*, not the product: whatever the platform
  does in the world, its marketplace text never says
  "notification", so it is not claimed. Reputation is not
  evidence.

No wording-artifact corrections were needed: the one raw hit is
the one claim, and its evidence sentence asserts the function it
tags (a messaging service, offered as a feature of the product).

## 3. Core-delta decision

| Claimed family (addition) | Disposition | Core delta |
|---|---|---|
| Messaging (1) | Core 4/5 — message composition + per-recipient delivery records; the family's Core side is the substrate itself | **Carried** — no change |

**Result: the core is unchanged.** The one function the newcomer
claims is the substrate the build already is (the family ranked
#1 in the union, now claimed by 9 of 11 forks). No records form
is missing: a targeted message is a composition addressed to
directory contacts/groups, dispatched per recipient over
configured channels through the reference transport, with
receipts labelled `reference_transport: true` — records and
metadata, never a real transmission, per the group's standing
discipline. `src/` is byte-identical to the shipped build
(`src/comm/store.py` SHA-256
`6ccd412c2c1a836694d74687804aa90abe31f4c54eba62e916c31cb6dc5e6110`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **11 forks** (10 original siblings + 1
remainder addition), **53 claims** in total (52 + 1), with
**11 of 11** forks carrying at least one claim. The merged build
remains the same 12-function communications substrate — directory,
channels, templates, composition, delivery records, dispatch
through the reference transport, scheduling, acknowledgement
tracking, immutable records & search, REST API, RBAC, append-only
audit — now spec'd against 11 marketplace offerings instead of
10. The group's character does not change: it was already
heterogeneous (security engines, archiving, notification,
casework, permits on one substrate), and the newcomer adds the
category's namesake citizen-communications platform in its
thinnest textual form — its substance beyond messaging
(marketing automation and targeting) is an engine, registered
below.

## 5. Gaps — for the registry at ship

**New gap function** (1):

- **Marketing automation & citizen-engagement campaign engine**
  (audience targeting / segmentation and automated campaign
  execution) — Granicus, from its own headline self-description
  ("the only FedRAMP-authorized marketing automation platform")
  and its named "Targeted Messaging Service" / "Advanced
  Package" offerings. The messaging substrate those campaigns
  ride is Core; the targeting and automation engine is
  Extended. The `workflow_automation` family claim did not
  fire on the fork's wording (recorded in §2), so this gap is
  registered from the fork's described function, not from a
  claim.

**Existing gaps gaining claimants:** none. `secure_transmission`
(E2E transport) explicitly gains **no** claimant: the fork's
"highly secure" / "most secure" prose is adjective framing
without the family's operative transmission phrasing, recorded
as a near-miss rather than a by-substance enlargement — the
contrast is the GRC addition's KSI case, where the function word
itself was present in singular form; here it is absent.
`notifications_alerts`' Core side gains no claimant either: the
description carries no notification token (§2).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  table, verbatim evidence, registry fields as published, the
  census citations (verified, tagging nothing), the near-miss
  pins, and the group totals (11 forks / 53 claims / 11 of 11
  claiming) — see `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a targeted message composed to a directory group, dispatched
  through the reference transport with a labelled receipt, and
  acknowledged (`ack_status` drains to zero pending); and a
  send-gate case — an sms delivery with no sms channel
  configured fails with `no_enabled_channel`.
- **Tests: 82 → 92, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the send-gate
  condition in `CommStore._dispatch_deliveries`
  (`if channel is None:` following the `_first_enabled_channel`
  lookup in `src/comm/store.py`) was patched to `if False:` and
  the full suite ran — **92 tests, exactly 5 failures**: the
  shipped drill's 4 plus 1 from the new additions module (the
  Granicus send-gate substrate case), tripping exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`.
