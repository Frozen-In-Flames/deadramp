# Addendum — Governance, Risk, and Compliance (GRC), CMMC L3-adjacent: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:grc-l3`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 10-function core,
its High control baseline, and its core-boundary decision are
**unchanged**. This document records what joined, what the
newcomer claims under the group's existing taxonomy (nothing),
the core-delta decision, and the updated union statement.

**Headline: forks spec'd 1 / 1; 0 new claims — a zero-claim
fork; core delta — zero functions extended, `src/`
byte-identical; tests 166 → 180, all passing.** The category's
standing named absence at this tier, `policy_management`,
**survives**: the newcomer contains no policy token, so the
family stands at 0 of 2 at L3-adjacent. **2 new gap functions**
are named in §5, both registered from the fork's described
function rather than from any claim, and 1 already-registered
gap gains a member by substance.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2122140784A` | Covergent Solutions Inc dba Exiger Government Solutions (EGS) / Exiger Federal Cloud (EFC) - High |

Census membership was verified against `remainder.json` before
building (unit `addition:grc-l3`, `fork_ids ==
["FR2122140784A"]`, `extends_group == "grc-l3"`). Note the
trailing **A** in the FedRAMP ID: `forks.json` also carries the
Moderate sibling record `FR2122140784` (same vendor, product
"Exiger Federal Cloud (EFC)", filed under Analytics at L2). The
two records share one identical description; they are separate
registry offerings, and only the High record is this unit's
member — nothing in this addendum depends on the sibling.

Method, identical to the original pass and to the GRC L2
addition:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast`** (parsed, never executed,
  never re-typed), asserts the taxonomy's 14 (id, label, regex)
  triples, and re-applies the original sentence splitting and
  first-match evidence rule. Before tagging the newcomer, the
  extractor **reproduces the original fork's shipped claim
  table exactly** from the cached description — US AI:
  `continuous_monitoring` + `risk_management`, evidence
  sentences included, deep-equal — and asserts the original
  sheet deep-equal to git HEAD. The new sheet is **appended**
  to `specs/specs.json`; the original sheet is byte-preserved
  through its closing brace (asserted in the extractor).
- The original extractor records its wording-artifact
  corrections as prose in its docstring (no CORRECTIONS literal
  exists); they were applied by the same reasoning, and the
  mechanical ones are asserted in the extractor: only
  `service_desc` is matched; no hosted-services exclusion is
  invented (the newcomer's `certified_services` is empty and
  no scope-exclusion segment exists — asserted); category and
  program names earn no tags, and neither do product module
  names; bare "risk" earns no tag (the `risk_management`
  pattern requires "risk management / risk tracking / risk
  register / risk assessment").
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is
  FedRAMP **High** / Certified, SaaS, Public Cloud, so the
  group stays single-tier and the High baseline is inherited
  in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: the
  fork's **1 census citation** was re-checked against its own
  cached description and **verifies verbatim** — it is the
  description's only sentence, i.e. the entire description.
  It tags no family (see §2): verification ≠ claim, and census
  classification ≠ claim either, in both directions.

## 2. What the addition claims

**0 claims.** The newcomer's entire marketplace description is
one sentence of 243 characters:

> "Exiger Government Solutions (EGS) developed a
> Software-as-a-Service (SaaS) product named 1Exiger which
> provides access to multiple modules - Due Diligence
> Intelligence (DDIQ), Third Party Management (3PM), Supply
> Dynamics (SDX), and Analytics."

Under the taxonomy applied verbatim it produces **0 raw hits
across all 14 families** — there is nothing for the
wording-artifact corrections to correct and nothing was
manufactured. The census classified the fork to GRC by
substance ("Thin description: only module names are given; due
diligence and third-party management are the named risk
functions"), and that classification is recorded on the sheet
as the census proposal; the claim pass reads the same text for
functional pattern phrases and finds none. Both statements are
true at once, and the difference between them is the group's
discipline working as designed.

Group claim counts after the addition (2 forks): the total
stays **2** — `continuous_monitoring` 1, `risk_management` 1,
both from US AI's Archangel passage; the other 12 families
stand at 0 of 2, and **`policy_management` stands at 0 of 2 —
the named absence survives at this tier** (its retirement at
L2 by the Group 33 addition was earned there by claimed
records forms; a retirement does not carry up a tier on its
own, and neither fork at High claims the family).

### Near-misses, itemized

The description's phrases, one by one (the full sentence map
is `scratch/additions_sentence_map.json` — a single sentence
with an empty hit list):

- **"Third Party Management (3PM)"** is third-party *risk*
  management in substance, but the word "risk" appears
  **nowhere in the description at all**, and "Third Party
  Management" contains none of the `risk_management` pattern
  phrases. Substance without the phrase earns no tag
  (Group 33 correction: bare "risk" earns no tag — here even
  the bare word is absent). The substance is registered as a
  gap in §5.
- **"Due Diligence Intelligence (DDIQ)"** is assessment-adjacent
  substance; `assessment_authorization` requires
  authorization-readiness / ATO / assessor phrasing, and
  `evidence_management` requires evidence phrasing — neither
  appears.
- **"Supply Dynamics (SDX)"** is supply-chain visibility in
  substance; no family covers it (US AI's supply-chain *risk*
  substance at this tier rode in on the literal "risk
  management" phrase in a functional sentence — the phrase,
  not the topic, is what the pattern matches). Registered as
  a gap in §5.
- **"Analytics"** (the fourth module) is not
  `posture_reporting`: the family requires compliance-posture /
  monitoring-dashboards / centralized-view phrasing. A bare
  module name names no reporting function, and — per this
  category's standing doctrine — **no score follows from it**
  either.
- **"provides access to multiple modules"** is not
  `identity_access_hooks`: the family requires "identity and
  access controls" or "role-based access control". "Access"
  alone is not the phrase.
- **"Software-as-a-Service (SaaS)"** is not
  `platform_hosting`: the family requires "Platform as a
  Service (PaaS)" / PaaS-architecture / secure-hosting
  phrasing. SaaS is not PaaS, and the fork's deployment model
  is its platform layer regardless — it transfers nothing to
  the build.
- **"developed a … product named 1Exiger"** is product
  self-description — marketing prose, no tags, per house
  method.

### Wording artifacts

None. Zero raw hits means no claim stands on an artifact, and
no artifact had to be pinned at reduced weight. The absence of
artifacts is itself recorded because the category's precedents
(a `risk_management` claim firing on the "Risk Management
Framework" program name at L2; "Authorization to Operate"
failing the taxonomy's "Authority to Operate" phrase) show the
failure mode this fork simply does not present.

## 3. Core-delta decisions

The newcomer claims no family, so no family's disposition
changes. The per-family state at this tier, for the record:

| Family | Disposition (UNION-SPEC) | Claimed at this tier | Core delta |
|---|---|---:|---|
| Continuous monitoring | Core records substrate; engine Extended | 1 (US AI) | **Carried** |
| Risk management | Core records substrate; prediction engine Extended; no scoring | 1 (US AI) | **Carried** |
| Evidence management & validation | Core — evidence registry | 0 | **Carried** |
| Security indicators (KSI) tracking & validation | Core — indicator registry | 0 | **Carried** |
| Vulnerability & remediation management | Core — finding records | 0 | **Carried** |
| Control & framework compliance management | Core — catalog registry | 0 | **Carried** |
| Compliance posture reporting & dashboards | Core — counts only, no scores | 0 | **Carried** |
| Assessment & authorization support | Core — assessment & authorization records | 0 | **Carried** |
| Audit support & assessor review | Core — append-only audit | 0 | **Carried** |
| Platform hosting / enclave operations | Platform layer | 0 | **Carried** |
| Identity & access controls (hooks) | Core — RBAC | 0 | **Carried** |
| Workflow & automation | Core seed — enforced lifecycles; engines Extended | 0 | **Carried** |
| APIs & integrations | Core — REST API | 0 | **Carried** |
| Policy management | **Named absence** — not built, not a gap | 0 | **Absence survives** |

**Result: the core is unchanged.** A zero-claim fork
presupposes no records form; the singleton's core-boundary
decision stands verbatim — all 10 core functions remain
**carried, not claimed** for this tier, now for both forks
(US AI's two engine claims continue to presuppose exactly this
substrate, and the Merge Rule carries the union up whole;
thinner prose at the same tier is not a downgrade). `src/` is
byte-identical to the shipped build (`src/grc/store.py`
SHA-256 `0fe88eb1f8099a30750accc4ebe2afaa36adafbea845b36bd796b42f33507025`
and `src/grc/audit.py` SHA-256
`df7b1ef9cb00458f1a56673900bf05b30a855fd4dede1f6e24e9ac4647abcb34`
before and after this addendum's work, both mutation drills
included; the full `src/` diff is empty). The tier baseline
does not change: same tier by construction. And no score is
introduced or implied anywhere: the newcomer's "Analytics"
module name changes nothing about the counts-only posture
surface, which the additions tests scan recursively for
score-like keys.

## 4. Updated union statement

The group now covers **2 forks**, **2 claims** in total, with
**1 of 2** forks carrying at least one claim. The merged build
remains the same 10-function GRC records substrate — framework
& control catalog, governed-system registry, indicator
registry, evidence registry, finding/POA&M records, assessment
& authorization records, counts-only posture, REST API, RBAC,
hash-chained append-only audit — at the High baseline, now
spec'd against 2 marketplace offerings instead of 1. The
group's character is unchanged and, if anything, confirmed:
neither High fork is a GRC product in its own right. US AI is a
nine-suite AI platform whose GRC slice is one suite; the
newcomer is a third-party-risk platform whose entire High
listing is a module catalogue. The category at this tier
remains a carried substrate with a thin claimed surface, and
the spec record now says so against two offerings instead of
one. `policy_management` remains a named absence at this tier;
every other family remains carried Core or platform layer, as
the union spec ranked them.

## 5. Gaps — for the registry at ship

**New gap functions** (2) — both registered from the fork's
described function (its own module names), **not** from claims:

- **Third-party risk & due-diligence intelligence platform**
  (DDIQ due-diligence intelligence; 3PM third-party
  management: third-party risk research, diligence, and
  management over vendors and counterparties) — Exiger. The
  findings such work produces are ingestible by Core 5 today;
  the research/intelligence machinery is Extended.
- **Supply-chain risk visibility & analytics platform**
  (SDX Supply Dynamics; the Analytics module: supply-chain
  dynamics visibility and analytics over them) — Exiger. Any
  scoring or prediction machinery belongs to this gap and to
  the risk-prediction gap below, never to the Core's posture
  surface.

**Existing gaps gaining a member by substance (no claimant):**

- **AI risk prediction engine** (registered in UNION-SPEC from
  US AI's Archangel passage: predicting global security and
  supply-chain risks) — +1 **by substance**: the newcomer's
  third-party and supply-chain risk surface is the same
  problem area, asserted through module names only. No claim
  fired, so no claimant is counted at claim level; the
  substance is booked once, here, and not double-booked under
  `risk_management`.

**Explicitly no claimant:**

- **Posture / risk scoring engines** — gains **no** claimant:
  the newcomer's bare "Analytics" module name presupposes no
  computed score, and this group's doctrine is that the Core
  computes none and no claim here licenses one.
- **Continuous-monitoring feeds & scanner integrations**,
  **automated evidence-validation engine**, **FedRAMP package
  generation** — all gain no claimant: the description
  contains no monitoring, evidence, or package phrase of any
  kind (token-verified in the additions tests).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the original
  fork's claim table standing exactly, the literal zero-claim
  table and the whole-taxonomy zero-claim set for the
  newcomer, tier fields, the description verbatim against the
  cached source, census citation accounting, the no-exclusion
  pin, the `policy_management` absence pin, and the near-miss
  pins (see `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests: a third-party-risk finding on a governed system
  with severity recorded verbatim, its due-date status derived
  at read (current on the due date, overdue after, never
  stored), over a recursively score-free posture surface; and a
  due-diligence evidence record (metadata + SHA-256,
  verify-by-content original True / tampered False, reviewer
  separation enforced) with an indicator result recorded
  verbatim.
- **Tests: 166 → 180, all passing.**
- **Negative controls:** the core is unchanged, so **both** of
  the group's signature drills were re-run in this tree.
  Drill 1 (status derivation): `derive_finding_status` patched
  so the overdue branch never fires (scoped patch, occurrence
  count asserted = 1) — **180 tests, exactly 9 failures**: the
  shipped drill's 8 plus exactly 1 from the additions module
  (the third-party finding derivation case), tripping as
  designed. Drill 2 (audit verifier): `verify_chain` patched
  to return `(True, None)` unconditionally (scoped patch,
  count asserted = 1) — **42 audit tests, exactly 4
  failures**: the shipped drill's identical set; the additions
  module adds no audit-chain case and no failure. Both files
  were restored from the pre-mutation copies and verified
  SHA-256-identical to the shipped hashes; the suite re-ran
  green. Recorded in `tests/README.md`; raw outputs in
  `scratch/additions_mutation_run.txt` and
  `scratch/additions_mutation_audit_run.txt`.
