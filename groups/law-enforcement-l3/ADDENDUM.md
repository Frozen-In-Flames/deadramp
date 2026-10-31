# Addendum — Law Enforcement, CMMC L3-adjacent: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:law-enforcement-l3`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its
11-function carried core, its core-boundary decision, and its
control baseline are **unchanged**. This document records what
joined, what the newcomer claims under the group's existing
taxonomy, the core-delta decision, and the updated union
statement.

**Headline: fork spec'd 1 / 1; 0 new claims (group total stays
0 across 3 forks — the newcomer is the group's third zero-claim
sheet, with 0 raw hits across all 9 families); core delta —
zero functions extended, `src/` byte-identical; tests 102 →
110, all passing.** The newcomer is a physical threat-detection
and incident-reporting network for law-enforcement and
force-protection organizations. Its description speaks a third
vocabulary this category's legal-research taxonomy does not
reach — the original pair spoke digital forensics; this fork
speaks threat detection over human incident reports. The
functions it describes in its own words — real-time threat
detection and alerting, incident reporting, pattern analysis,
originator-controlled information sharing, mass warning and
notification, and an integration API — are itemized in §5 as
this fork's own verticals, every one **Extended**. **6 new gap
functions** are named in §5; no existing gap gains a claimant;
the category-discipline accounting (what the text does *not*
assert) is pinned at the token level in §2.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1602057825A` | TRAPWIRE / TRAPWIRE Threat Detection and Analysis System |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact (id, label, regex)
  triples** — and, because this group's taxonomy is inherited
  from Group 34, the extractor also parses the taxonomy out of
  `groups/law-enforcement-l2/scratch/extract.py` and **asserts
  the two are equal**: the verbatim-inheritance proof, not a
  claim about it. Same sentence splitting, same evidence rule
  (first matching sentence per family), same sheet schema.
- **Corrections:** neither this group's extractor nor Group
  34's carries a programmatic `CORRECTIONS` literal (asserted
  in the extractor). The original pass's four wording-artifact
  corrections are prose-level — the taxonomy is applied
  byte-for-byte with no pattern widened; an integrity assurance
  about a vendor's own process tags nothing; assurance prose
  about an offering's own authorization posture is not an
  access-control claim; no claim is inferred from the category
  label itself — and they are applied here as recorded judgment
  (§2), not as code.
- **Reproduction before tagging:** the extractor first rebuilt
  the original 2 forks' sheets from the raw cache with the
  original construction, and both came out **deep-equal to the
  shipped sheets, claim tables included** (both empty, as
  shipped — the shipped tables are the ground truth and they
  reproduced exactly). Only then was the newcomer tagged. The
  new sheet is **appended** after the originals, which are
  byte-for-byte untouched (the re-serialized file is
  byte-preserved through the original sheets' closing brace;
  asserted in the extractor, on top of the parsed
  deep-equality).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. No live
  fetching. The fork is FedRAMP **High / Certified** (SaaS,
  **Public Cloud** — the group's first Public Cloud member; the
  deployment model is the source record's field and changes no
  baseline), so the L3-adjacent baseline is inherited in full,
  unchanged.
- **Category provenance, stated plainly:** forks.json files
  this fork as "Uncategorized (none in source)" and its source
  record carries an **empty** business_categories list. The
  census assigned Law Enforcement from the fork's own
  description (its classifier note: "Physical threat detection
  for law-enforcement/anti-terrorism network, not cyber"), and
  that assignment is what this unit extends; the sheet records
  `deadramp_category: "Law Enforcement"` on that basis.
- The census starting point was verified, not trusted: the
  fork's **2 census citations** were re-checked against its own
  cached description and **verify verbatim (2 / 2)** — and
  neither tags a family, recorded in §2: verification is not a
  claim, in either direction.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty (asserted in the
  extractor), and only `service_desc` was matched, per house
  method. The description's tool list (incident reporting,
  pattern analysis, threat detection, information sharing, mass
  warning, collaboration) is the fork's **own** suite, not a
  catalogue of third-party hosted applications and not a
  scope-exclusion segment; it was matched as the fork's own
  prose and fired nothing. **No raw hit was removed** — there
  were no raw hits: the sentence map (`scratch/
  additions_sentence_map.json`) records 0 matching sentences
  for every one of the 9 families.

## 2. What the addition claims

**0 claims** under the 9-family taxonomy applied verbatim. The
group total stays **0** (Cellebrite 0, Magnet One 0, TRAPWIRE
0); all 9 families stand at 0 of 3 forks.

### Near-misses, itemized per sentence

- **Sentence 1** (census citation 1: "…a software platform for
  detecting and alerting on threats against your assets and
  personnel in real-time") — the fork's headline function in
  its own words; no taxonomy family covers threat detection
  (§5, vertical 1). "Assets and personnel" are the protected
  objects, not evidence, records, or persons this build holds.
- **Sentence 2** ("…one centralized, highly secure and
  encrypted platform, including:") — platform assurance prose
  about the fork's own platform. It is not the verbatim
  `access_control` phrase ("secure access controls") and not
  the verbatim `hosting_platform` phrase ("secure cloud
  environment"); per the original correction 3's shape,
  assurance prose tags nothing.
- **The tool-list bullets** ("- Incident reporting", "- Pattern
  analysis", "- Threat detection", "- Originator-controlled
  information sharing", "- Mass warning and notification",
  "- Cross-organizational collaboration") — the fork's own
  function enumeration, booked as verticals in §5. The
  collaboration bullet is the group's third `collaboration`
  near-miss: the substance is present, the verbatim pattern
  ("save, annotate, share and collaborate") is not.
- **Sentence 9** ("…a web-based software-as-a-service offering
  that provides secure web access to a suite of incident
  reporting, analytical, and information sharing tools") —
  "secure web access" (occurrence 1 of 2) is access prose, not
  "secure access controls"; and although the offering is SaaS,
  `hosting_platform` does not fire: **the word "cloud" appears
  nowhere in the description** (count-verified) — the Public
  Cloud deployment model is the source record's field, not
  description text.
- **Sentence 10** ("…each Agency owns its data and determines
  what other organizations its users may collaborate with") —
  originator control asserted in substance (§5, vertical 4);
  "may collaborate with" is not the verbatim collaboration
  phrase.
- **Sentence 11** ("In addition to secure web access, the
  following services are available:") — occurrence 2 of "secure
  web access"; lead-in prose, tags nothing.
- **Sentence 12** (the Mobile App: "Enables real-time incident
  reporting and feedback… in a mobile environment such as VIP
  or perimeter protection") — real-time occurrence 2; the field
  reporting channel of §5 vertical 2.
- **Sentence 13** (the Community Member App: "…report
  suspicious activity in a structured manner through publicly
  accessible apps…") — community suspicious-activity reporting
  (§5, vertical 2). "Structured" is not "search": the
  description contains **no "search" token at all**
  (count-verified), so `legal_search` has nothing to miss on.
- **Sentence 14** ("The TrapWire API: Provides for integration
  between a TrapWire System deployment and legacy or other
  enterprise systems, enabling a system-of-systems approach to
  data integration.") — an integration API asserted in its own
  words (§5, vertical 6); no taxonomy family covers it.
- **Sentence 15** (census citation 2: "…detects and alerts on
  mutual threats spanning time and geography, allowing users to
  break down stovepipes and interdict threats before they
  materialize…") — the detection/alerting function restated
  with its interdiction purpose (§5, vertical 1).
- **Sentence 16** ("The network encapsulates thousands of
  protected facilities and personnel spanning Federal, State,
  and Local Law Enforcement; Anti-Terrorism/Force Protection
  personnel; …") — the network's membership and audience.
  "Law Enforcement" here is a sector in a list; per the
  original correction 4, no claim is inferred from the category
  label, in the fork's own text any more than in the registry's.
- **Sentence 17** ("…modern technology and expert analytical
  support services, while maintaining ""originator control""
  principles for each owner's data…") — originator control
  restated (§5, vertical 4); "expert analytical support
  services" is analyst support asserted in substance (§5,
  vertical 3).
- **Whole-description absences (count-verified, all zero):**
  no "document" token (so `document_management` has nothing to
  miss on); no "cloud"; no corpus, citation, editorial, or
  guidance token of any kind.

### Category-discipline accounting

Capabilities are attributed to this fork **only** where its own
listing text states them — reputation is not evidence,
anywhere, and doubly not in this category (the Singleton 47
precedent: facial recognition, predictive policing, and
real-time intelligence feeds appeared nowhere in that fork's
description and were not attributed to it). Token-verified
against this fork's description:

- **Facial recognition — not described, not attributed.** No
  "facial" or "recognition" token exists in the text.
- **Surveillance and sensor/camera monitoring — not described,
  not attributed.** No "surveillance", "camera", or "sensor"
  token exists. The fork's described inputs are human-filed
  incident reports (web suite, mobile app, community app), not
  feeds or sensors.
- **Predictive policing — not described, not attributed.** No
  "predict" token exists. The fork's own interdiction phrasing
  ("interdict threats before they materialize") is booked
  verbatim under its detection vertical in §5, not relabeled.
- **Real-time detection and alerting — described, in the
  fork's own words** ("detecting and alerting on threats …
  in real-time", twice). This is the one point where the
  newcomer touches the union spec's category-discipline line
  ("real-time intelligence feeds", written for the original
  pair, whose descriptions assert no such function). The
  distinction is recorded, not smoothed: the exclusion named
  feed-ingestion infrastructure; this fork describes real-time
  alerting over a **human incident-reporting network**. The
  described function is registered as this fork's vertical in
  §5 for union completeness, **Extended and not implemented**;
  the build's posture is unchanged — nothing in this substrate
  detects, alerts, ingests any feed, surveils, identifies, or
  predicts.
- **Criminal records — not described.** The word "criminal"
  occurs exactly once, in "successful criminal or terrorist
  acts" — acts to be interdicted, not records, history data, or
  case subjects. The Group 34 named absence (criminal records /
  RMS) survives in both senses.

## 3. Core-delta decision

The newcomer claims no family, so no family disposition moves:
all 9 families keep their union dispositions, and the 11 core
functions remain **carried, not claimed** — now for all 3
forks, under the same core-boundary decision recorded in
UNION-SPEC. The functions the newcomer asserts in substance
beyond the taxonomy (its six verticals) are booked as gaps in
§5, not built. **Result: the core is unchanged — delta zero
functions.** The substrate the newcomer's shape presupposes —
a membership boundary deciding who may see a network's records
(Core 1; the records-side analogue of the fork's originator
control: a member organization's records are visible to its
members and to no one else) and report records held as metadata
plus checksum with verify-by-content (Cores 3–4) — is the
substrate the build already is, exercised in the newcomer's
shape by the additions substrate tests. The analogue is stated
as an analogue: originator control over shared incident
content is Extended (§5, vertical 4); the substrate shares no
content. `src/` is byte-identical to the shipped build (all 7
`lawenf` modules SHA-256-verified against the pre-work hashes,
the mutation drill included; `src/lawenf/store.py` remains
`18070d5545505462439c5f62f76e2ce93ce428c8fb17774107f50c40bb2a6350`,
the hash the shipped tests/README records). The tier baseline
does not change: the group was High 2 and is now High 3.

## 4. Updated union statement

The group now covers **3 forks** (the original pair + 1
remainder addition), **0 claims** in total (0 → 0), with **0 of
3** forks carrying a claim. The merged build remains the same
11-function legal-research records substrate — matter registry
& members, source registry, document registry,
verify-by-content, saved-search records, annotation records,
citation-check records, registry reporting, registry search,
access control, and the hash-chained fail-closed audit log —
carried whole from Group 34 at the High baseline under the
core-boundary decision, now spec'd against 3 marketplace
offerings instead of 2. The group's character is stated
plainly: it is now three zero-claim sheets in three different
function vocabularies (digital forensics ×2, physical threat
detection ×1) measured against a legal-research taxonomy that
reaches none of them. The claims floor for the category at
L3-adjacent remains zero, and it is stated rather than padded;
the union's completeness comes from the verticals itemized in
the union spec and in §5 below, each resting on a verbatim
evidence sentence.

## 5. Gaps — for the registry at ship

**New gap functions** (6) — this fork's own verticals, each
registered from the fork's described function, each **Extended
— specified, not implemented**: every one operates over
operational incident content and live reporting flows, which
this records substrate never holds.

- **Threat detection & real-time alerting** — detecting and
  alerting on threats against assets and personnel in
  real-time, and on mutual threats spanning time and geography,
  with interdiction before threats materialize (sentence 1,
  the tool-list bullet, and sentence 15 — the fork's headline
  function). Registered
  with the §2 discipline note attached: the described input is
  a human incident-reporting network, not feeds or sensors;
  nothing in the build implements any part of it.
- **Incident reporting & structured suspicious-activity
  reporting** — incident-report intake across the web suite,
  the Mobile App's real-time field reporting, and the Community
  Member App's structured community reporting (tool list,
  sentences 9, 12, 13).
- **Pattern analysis & analyst support** — pattern analysis
  over incident reports, with expert analytical support
  services (tool list, sentence 17). An analysis engine over
  report content; the substrate's counts-on-read reporting is
  not this.
- **Originator-controlled cross-organizational information
  sharing** — sharing across a protection network where each
  owner retains control of its data and determines which
  organizations its users may collaborate with (tool list,
  sentences 9, 10, 17). Registered as its own vertical, on the
  non-conflation precedent: the group's existing vertical 7 is
  information sharing / collaboration **over evidence**
  (forensic objects, custody context); this fork's object is
  operational incident and threat reports under an
  originator-control model. Adjacent, distinct, not
  double-booked.
- **Mass warning & notification** — mass warning and
  notification across the network (tool list). A notification
  engine; no taxonomy family covers it and the substrate sends
  nothing.
- **Integration API & system-of-systems data integration** —
  the fork's API integrating a deployment with legacy and other
  enterprise systems (sentence 14). The Core is API-first for
  its own records; source-system integration is not part of it.

**Existing gaps gaining claimants: none.** The group's 8 own
verticals (device unlocking; evidence extraction; forensic
analysis engines; evidence ingest & processing; evidence
review; chain-of-custody enforcement; information sharing /
collaboration over evidence; forensic reporting) gain nothing
from the newcomer: it describes no forensic, evidence, or
device function ("assets and personnel" are protected objects,
not evidence). The carried Group 34 Extended set (the legal
corpora themselves, citation-validation engines, editorial
enhancement systems, corpus search & relevance engines, AI/ML
research assistance, document content storage / rendering /
redaction) gains nothing either.

**Named absences — the Group 34 set, re-checked at this tier.**
Incident / case management: **partially retired in substance**
— the newcomer describes incident *reporting* in its own
words (registered above), while case management as an
operational system (case lifecycle, assignment, disposition)
is described by no fork at this tier and that half of the
absence survives. Evidence management & chain of custody as an
operational system: survives for the newcomer (no evidence
function described; the group's vertical 6 stands on
Cellebrite alone). Criminal records / RMS: survives in both
senses (see §2). Investigative case files and case subjects:
survives — the fork names no case file and no case subject, and
this build's privacy discipline holds no shape that could hold
one.

**Platform notes for the addition fork** (stated so nothing is
implied): the fork's "highly secure and encrypted platform" is
its own platform property — no encryption, FIPS, or
authorization posture is inherited by this build (UNION-SPEC's
SC-13 gap stands); its Public Cloud deployment model is the
source record's field; its network scale ("thousands of
protected facilities and personnel") is the fork's operating
fact, not a property of this single-tenant reference build.
The baseline gaps at High named in UNION-SPEC (MFA /
authenticator management, FIPS-validated cryptography SC-13,
encryption at rest SC-28, audit retention AU-11, session lock /
termination AC-11/AC-12) are unchanged.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  tables (all three sheets empty, exactly as shipped for the
  originals and as tagged for the newcomer), the full
  zero-claim set (all 9 families at 0 of 3), descriptions equal
  to the cached marketplace text, both census citations
  verifying verbatim and tagging nothing, registry fields as
  published, the near-miss pins ("Cross-organizational
  collaboration" ≠ the verbatim phrase; "secure web access"
  ≠ "secure access controls"; no "cloud", "search", or
  "document" token anywhere), and the category-discipline pins
  (no facial / recognition / surveillance / camera / sensor /
  predict token; "real-time" present in the fork's own words;
  "criminal" exactly once, naming acts) — see
  `tests/test_additions.py`.
- The fork is exercised against the substrate in the same
  file: a protection-network matter whose membership boundary
  denies an outsider both the matter read and the record list
  while members read normally (Core 1), and a filed report's
  record — metadata + SHA-256 only, verify-by-content matching
  the exact bytes and rejecting altered bytes, a saved search
  stored as a digest with the query text nowhere in the record,
  and the matter report counting members, documents by status,
  and searches on read (Cores 3–5, 8). All are
  carried-substrate cases: the newcomer claims no family, and
  the addendum claims none on its behalf.
- **Tests: 102 → 110, all passing.**
- **Negative control: the group's signature drill was re-run
  in this tree.** The membership-guard mutation — the
  `PermissionDenied` raise in `_require_matter_access`
  (`src/lawenf/store.py`) replaced with `return None`, applied
  as a scoped replacement with the target text asserted to
  occur exactly once — and the full suite ran: **110 tests,
  exactly 6 failures** — the shipped drill's 5
  (`test_negative_control` canonical denial, `test_service`
  full-flow, `test_sources` outsider-cannot-list,
  `test_matters` outsider read denied and outsider scoped-write
  denied) plus exactly 1 from the new additions module
  (`test_additions.TestTrapwireSubstrate.test_protection_network_membership_boundary`),
  tripping exactly as designed. `store.py` was restored from
  the pre-mutation copy (`scratch/store.py.premutation-additions`)
  and verified SHA-256-identical to the shipped hash
  (`18070d55…`); the full suite re-ran green after the restore.
  Recorded in `tests/README.md`; raw failure list in
  `scratch/additions_mutation_run.txt`.
