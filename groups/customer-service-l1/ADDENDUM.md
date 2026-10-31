# Addendum — Customer Service, CMMC L1: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:customer-service-l1`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 10-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomer claims under the group's
existing taxonomy (nothing), the core-delta decision, and the
updated union statement.

**Headline: fork spec'd 1 / 1; 0 new claims — a zero-claim fork;
core delta — zero functions extended, `src/` byte-identical;
tests 69 → 80, all passing.** The newcomer is the category's
canonical help-desk platform by reputation and its emptiest
description by text: three sentences of marketing prose containing
no taxonomy token at all. **1 new gap function** is named in §5,
one already-registered gap gains a by-substance member, and the
union spec's "no fork has zero claims" floor does **not** survive
the addition (see §2).

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1821856903` | Zendesk / Zendesk Customer Support and Help Desk Platform |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` and `CORRECTIONS` literals out of
  the original `scratch/extract.py` via `ast` (parsed, never
  executed, never re-typed) and tags with those exact (id, label,
  regex) triples** — the taxonomy was applied verbatim, not
  re-tuned for the newcomer. Same sentence splitting, same
  evidence rule (first matching sentence per family), same sheet
  schema, same wording-artifact corrections mechanism.
- **Reproduction before tagging:** the extractor first re-ran the
  original pass end to end — same join (forks.json category
  "Customer Service" + cmmc_tier "L1", sorted by source_url;
  descriptions from the cached GSA dataset) — and the 2 shipped
  sheets regenerated **deep-equal** to `specs/specs.json`,
  including the correction that keeps Riskuity's
  `compliance_frameworks` raw hit removed (reproduction raw hits:
  PagerDuty 7 → 7 claims; Riskuity 2 raw → 1 claim). Only then was
  the newcomer tagged. The new sheet is **appended** after the
  original 2, which are byte-for-byte untouched (the re-serialized
  file is byte-preserved through the second sheet's closing brace;
  asserted in the extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. No live
  fetching. The fork is FedRAMP **LI-SaaS / Certified** (SaaS,
  Public Cloud). The group was 2 × Low; the union spec's tier
  rule already covers this composition — the union of the Low
  and LI-SaaS parent baselines is Low (LI-SaaS is a tailored
  subset and adds nothing) — so the L1 baseline is inherited in
  full, unchanged, and the group composition is now Low 2,
  LI-SaaS 1.
- **Category provenance, stated plainly:** forks.json files this
  fork as "Uncategorized (none in source)" and its source record
  carries an **empty** business_categories list. The census
  assigned Customer Service from the fork's own description, and
  that assignment is what this unit extends; the sheet records
  `deadramp_category: "Customer Service"` on that basis.
- The census starting point was verified, not trusted: both
  **census citations** for this fork were re-checked against the
  fork's own cached description and **2 / 2 verify** as verbatim
  substrings — with the twist recorded in §2: both tag nothing.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty, its description contains
  no third-party catalogue and no scope-exclusion segment
  (asserted in the extractor). Only `service_desc` was matched,
  per house method. **No raw hit was removed: there were no raw
  hits at all.**

## 2. What the addition claims

**0 claims.** The fork's description is three sentences long; the
per-sentence map is `scratch/additions_sentence_map.json`, and
every sentence's family list is empty — **0 raw hits across all
16 families**, before any correction. The group's claim total is
unchanged at 8 (PagerDuty 7, Riskuity 1, Zendesk 0).

**The floor does not survive, stated plainly.** The union spec
recorded "No fork has zero claims" for the original pair. That
sentence is now false of the enlarged group: **1 of 3 forks
(Zendesk) has zero claims**, and a second (Riskuity) still has
zero *customer-service* claims. The category's namesake help-desk
product contributes no function claims whatsoever, because its
marketplace text never names a function. Nothing was invented to
rescue the floor.

### Near-misses, itemized per sentence

- **Sentence 1** ("Zendesk is a cloud-based customer service
  platform, designed for companies that want to build customer
  relationships that are more meaningful, personal, and
  productive.") — this is the census's classification sentence
  and it tags nothing. `case_ticket_management` requires a
  ticket/case token ("customer support tickets", "tickets",
  "cases", "triag…"); the sentence has "customer service" and
  "customer relationships", neither of which is a token.
  "relationships … meaningful, personal" is relationship
  aspiration, not a function assertion. The product's *name* —
  "Customer Support and Help Desk Platform" — is not description
  text and is never matched; it contains no taxonomy token
  either ("help desk" is not a family pattern; `knowledge_base`
  requires "help article").
- **Sentence 2** ("Zendesk strives to bring businesses and
  customers closer together by enabling companies to provide
  great support and mature with self-service and proactive
  engagement.") — "self-service" misses `knowledge_base` on the
  missing word "article" (the family is "self-service *article*";
  the bare capability is asserted in substance and is booked in
  §5, not claimed). "provide great support" tags nothing:
  "support" alone is no family's token (`realtime_channels`
  requires "phone support" / "live chat" / telephony phrasing,
  all absent). "proactive engagement" asserts outreach in
  substance; no family covers it — it becomes the gap in §5.
- **Sentence 3** ("It is designed to be easy to use, customize,
  and scale.") — ease-of-use and scale prose; tags nothing, and
  platform qualities (cloud-based, scale) are the fork's own
  deployment properties, which do not transfer to the build.
- **Whole-description absences** — no ticket, case, chat, survey,
  dashboard, audit, or access token appears anywhere in the
  text. Whatever the platform does in the world, its marketplace
  description says none of it. Reputation is not evidence.

**The census-citation twist, in its purest form.** Both census
citations verify as verbatim description text, and **both tag
nothing** — they are the description's first two sentences. The
census classified the fork correctly by reading those sentences
for substance; the claim pass reads the same sentences for
function tokens and finds none. Verification is not a claim, in
both directions, and classification is not a claim either.

## 3. Core-delta decision

The newcomer claims no family, so there is no per-family delta to
decide: no claimed function is missing a records form, and no
form was added on the strength of unclaimed prose. **Result: the
core is unchanged.** The substrate the fork's described function
presupposes — cases with a lifecycle, requesters held by opaque
reference, assignment, due records with breach derived at read,
public status updates — is the substrate the build already is,
exercised in the newcomer's shape by the additions substrate
tests and recorded as **carried, not claimed**, the same status
access control and audit logging hold in this group. `src/` is
byte-identical to the shipped build (all 7 `custsvc` modules
SHA-256-verified against the pre-work hashes, the mutation drill
included; `src/custsvc/store.py` remains
`05c749f34c37a977e76cb1372c035909ad09875a7180ff441ac876a489cffe06`).
The tier baseline does not change: LI-SaaS adds nothing to the
Low union, per §1.

## 4. Updated union statement

The group now covers **3 forks** (2 original siblings + 1
remainder addition), **8 claims** in total (unchanged), with
**2 of 3** forks carrying at least one claim. The merged build
remains the same 10-function customer-service records substrate —
case registry and lifecycle, opaque-reference requesters,
assignment, priority/due records with derived breach, alert
records, on-call rotations, derived status communication, a
never-executing rule registry, registry reporting and search,
RBAC and append-only audit — now spec'd against 3 marketplace
offerings instead of 2. The group's character, already stated in
the union spec, sharpens rather than changes: it was largely a
source-category artifact in which only PagerDuty's claims
describe the substrate, and it now also contains the category's
canonical product contributing nothing but its tier and its
census classification. The two non-PagerDuty members arrive by
opposite routes — Riskuity filed *into* the category by the
source while being a GRC platform, Zendesk filed *nowhere* by
the source while being the category's namesake — and the spec
records both routes rather than smoothing them over.

## 5. Gaps — for the registry at ship

**New gap function** (1):

- **Proactive engagement & outreach** — proactive customer
  engagement and outbound outreach (campaigns, nudges,
  re-engagement) asserted in substance by the fork's own words
  ("mature with self-service and proactive engagement"). No
  taxonomy family covers outreach; the case/status substrate it
  would ride is Core, the engagement engine is Extended.
  Registered from the fork's described function, not from a
  claim — the family claim did not fire because no family
  exists.

**Existing gaps gaining a member by substance** (1):

- **Knowledge base articles / self-service** — Zendesk asserts
  "self-service" in its own words. The claim-level named absence
  **stands** (0 of 3 forks claim `knowledge_base`; the family's
  operative word "article" is absent), but the gap is no longer
  memberless in substance: the self-service capability the gap
  names is described by this fork. Booked as an enlargement by
  substance, exactly as the Communication L3 addendum booked its
  search enlargement — the function phrase is present, the
  family's claim token is not.

**Existing gaps explicitly gaining no claimant:**

- **Real-time channels** stays at 0 of 3 claims. The fork is
  known in the world for live chat; its listing contains no
  channel token of any kind, so the gap gains no claimant.
  Reputation is not evidence.
- **AI assistance / deflection** gains no claimant: the
  "self-service" substance is booked under knowledge base above,
  and no AI / virtual-agent / learned-model token exists in the
  text; the same phrase is not counted twice.
- **Satisfaction / CSAT surveys** — the named absence survives
  untouched: no survey token, no substance asserted, 0 of 3.
- Case/ticket, SLA, and notification-delivery positions are
  unchanged: the case substrate is Core (claimed by PagerDuty
  alone, still 1 of 3), and the fork asserts no due/SLA or
  delivery function in words or substance.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  tables (the newcomer's empty table and the originals' tables
  exactly as shipped), the zero-claim set (all 16 families),
  verbatim census citations tagging nothing, registry fields as
  published, the near-miss pins, and the group totals (3 forks /
  8 claims / 2 of 3 claiming / the case family at 1 of 3) — see
  `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a help-desk case flow — opaque-reference requester, assignment,
  lifecycle, a public update surfacing in the derived public
  status view while an internal note never does, resolution
  returning the view to operational — and a breach-derivation
  case (below). Both are carried-substrate cases: the fork
  claims no family, and the addendum claims none on its behalf.
- **Tests: 69 → 80, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `CustsvcStore.
  _is_breached` in `src/custsvc/store.py` was patched to
  `return False` unconditionally (scoped replacement of the
  function's body, asserted to occur exactly once) and the full
  suite ran — **80 tests, exactly 8 failures**: the shipped
  drill's 7 plus 1 from the new additions module
  (`test_additions.TestZendeskSubstrate.
  test_due_case_breach_derivation`), tripping exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`, raw list in
  `scratch/additions_mutation_run.txt`.
