# Addendum — Cybersecurity & Risk Management, CMMC L1: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:cybersecurity-l1`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 11-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomer claims under the group's
existing taxonomy (nothing), the core-delta decision, and the
updated union statement.

**Headline: fork spec'd 1 / 1; 0 new claims — a zero-claim fork;
core delta — zero functions extended, `src/` byte-identical;
tests 194 → 205, all passing.** The newcomer is the category's
best-known crowdsourced security-testing platform by reputation
and, by its marketplace text, a description of a *human* function —
a researcher community and a disclosure service — in a taxonomy of
tool functions: it produces **no raw hit across any of the 25
families**. **1 new gap function** is named in §5, no existing gap
gains a claimant, and the union spec's "no zero-claim forks" floor
does **not** survive the addition (see §2).

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1919750997` | HackerOne / HackerOne Continuous Security Testing Platform |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact (id, label, regex) triples** —
  the taxonomy was applied verbatim, not re-tuned for the newcomer.
  Same sentence splitting, same evidence rule (first matching
  sentence per family), same 400-char evidence truncation, same
  sheet schema.
- **There is no `CORRECTIONS` literal in this group's extractor —
  asserted in the additions extractor.** Group 4's four
  wording-artifact corrections are inherited *inside* the
  taxonomy's regex design itself (strong markers required for
  `compliance_grc`, an automation object required for
  `automation`), exactly as the union spec records; there is no
  separate corrections table to apply, and none was invented.
- **Reproduction before tagging:** the extractor first re-ran the
  original pass end to end — same join (forks.json category
  "Cybersecurity & Risk Management" + cmmc_tier "L1", in forks.json
  order; sheet fields built from the cached product records exactly
  as the original built them) — and the 5 shipped sheets
  regenerated **deep-equal** to `specs/specs.json` (claim tables:
  Anitian 2, Drata 5, IntelliGRC 2, MapLarge 1, Valimail 3 — 13 in
  total). Only then was the newcomer tagged. The new sheet is
  **appended** after the original 5, which are byte-for-byte
  untouched (the re-serialized file is byte-preserved through the
  fifth sheet's closing brace; asserted in the extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. No live
  fetching. The fork is FedRAMP **LI-SaaS / Certified** (SaaS,
  Public Cloud). The group was Low 4 + LI-SaaS 1 (Valimail); the
  newcomer is the group's second LI-SaaS member. LI-SaaS is a
  tailored subset of the Low baseline and adds nothing to the
  union, so the L1 baseline is inherited in full, unchanged, and
  the group composition is now Low 4, LI-SaaS 2.
- **Category provenance, stated plainly:** forks.json files this
  fork as "Uncategorized (none in source)" and its source record
  carries an **empty** business_categories list. The census
  assigned Cybersecurity & Risk Management from the fork's own
  description, and that assignment is what this unit extends; the
  sheet records `deadramp_category: "Cybersecurity & Risk
  Management"` on that basis.
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

**0 claims — 0 raw hits across all 25 families, before any
correction question can arise.** The fork's description is three
sentences long; the per-sentence map is
`scratch/additions_sentence_map.json`, and every sentence's family
list is empty. The group's claim total is unchanged at 13
(Anitian 2, Drata 5, IntelliGRC 2, MapLarge 1, Valimail 3,
HackerOne 0).

**The floor does not survive, stated plainly.** The union spec
recorded "All 5 of 5 offerings carry at least one tagged claim
(13 claims total), so there are no zero-claim forks in this
group." That sentence is now false of the enlarged group: **1 of
6 forks (HackerOne) has zero claims**. Nothing was invented to
rescue the floor.

### Near-misses, itemized per sentence

- **Sentence 1** ("HackerOne is a multi-tenant Vulnerability
  Disclosure and crowdsourced Bug Bounty platform.") — this is
  the census's classification sentence and it tags nothing.
  `vuln_management` requires "vulnerability" followed by a
  scanning/scan/management/assessment/data/repository object (or
  a consolidation/exposure marker); "Disclosure" is none of
  those objects. "Bug Bounty" is no family's token — the taxonomy
  has no crowdsourced-testing family at all (see §5).
- **Sentence 2** ("Organizations rely on HackerOne to detect
  unknown security vulnerabilities in public-facing systems as
  well as sensitive assets that are not publicly disclosed.") —
  this is the census's second citation and it also tags nothing.
  `detection_response` requires a threat-detection, SIEM/SOAR/MDR,
  security-operations, incident-response, or threat-hunting
  marker; the bare verb "detect" aimed at vulnerabilities is
  none of them. `asset_inventory` requires an
  inventory/visibility/discovery/attack-surface marker;
  "sensitive assets" is a noun phrase about the targets, not an
  inventory function.
- **Sentence 3** ("This is done by giving customers access to
  the world's largest community of crowdsourced security
  researchers. Researchers then conduct remote, internet based,
  crowdsourced vulnerability discovery and disclosure services
  against internet-accessible assets, including public-facing
  websites, networks, systems, and applications.") —
  `vuln_management` misses again ("discovery" is not in its
  object list). "giving customers access to …" tags neither
  `identity_access` (no identity, authentication, MFA, SSO, or
  privileged-access token) nor `access_control_feature` (no
  RBAC, access-control, least-privilege, or policy-enforcement
  token). `endpoint_management` requires the contiguous phrase
  "remote access"; the text has "remote, internet based" — the
  comma is the miss, recorded at token level.
- **Whole-description absences** — the word **"testing" appears
  nowhere in the description**. It lives only in the product's
  *name* ("HackerOne Continuous Security Testing Platform"), and
  names are never matched, so `app_security` (penetration
  testing, security testing, web app scanning, SAST/DAST/SCA)
  does not fire — on the listing of a security-testing platform.
  There is likewise **no "risk" token anywhere** (`risk_scoring`
  cannot fire), and no dashboard, reporting, audit, encryption,
  API, telemetry, or automation token. Whatever the platform
  does in the world, its marketplace description says it in
  human terms the tool taxonomy does not read. Reputation is
  not evidence.

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
presupposes — a register where vulnerability findings land, a
deterministic published score per finding, triage and assignment,
control linking at ingest, posture reported as counts — is the
substrate the build already is: a researcher report is a finding
in the same register scanner output lands in, exercised in the
newcomer's shape by the additions substrate tests and recorded
as **carried, not claimed**. `src/` is byte-identical to the
shipped build (all 8 `cyber` modules SHA-256-verified against
the pre-work hashes, the mutation drill included;
`src/cyber/store.py` remains
`f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de`,
the hash the shipped tests/README records for it). The tier
baseline does not change: LI-SaaS adds nothing to the Low union,
per §1. One scoring note, stated plainly: the only score this
build computes is the published deterministic finding formula
(severity weight × asset criticality weight, pinned by
`test_scoring.py`); posture reporting is counts only, and no
risk score is computed from this fork's prose or anywhere else.

## 4. Updated union statement

The group now covers **6 forks** (5 original siblings + 1
remainder addition), **13 claims** in total (unchanged), with
**5 of 6** forks carrying at least one claim. The merged build
remains the same 11-function defensive platform substrate —
asset inventory, finding ingestion (single/bulk/CSV, atomic),
finding triage & lifecycle, deterministic risk scoring, the risk
register, control mapping & assessment, search & filtering,
posture reporting, API access, access control, and the
append-only audit log — now spec'd against 6 marketplace
offerings instead of 5. The group's character sharpens rather
than changes: it was already a light-tier group dominated by
GRC/compliance platforms, and it now also contains the
category's canonical crowdsourced-testing platform contributing
nothing but its tier and its census classification. The two
non-GRC routes into this group are both recorded rather than
smoothed over: Valimail claims on DMARC protocol-name wording
(the union spec's own wording-artifact note), and HackerOne
arrives by census classification while claiming nothing at all.
All 17 families that stood at 0 claims remain at **0 of 6**.

## 5. Gaps — for the registry at ship

**New gap function** (1):

- **Crowdsourced security testing & disclosure coordination
  platform** — the researcher-community marketplace (recruiting,
  matching, and managing a community of independent security
  researchers), engagement management, and vulnerability
  disclosure coordination asserted across all three sentences
  of the fork's description ("crowdsourced Bug Bounty platform",
  "access to the world's largest community of crowdsourced
  security researchers", "crowdsourced vulnerability discovery
  and disclosure services"). No taxonomy family covers it:
  `vuln_management` is scanning/management *tooling*,
  `app_security` is testing *engines* (SAST/DAST/SCA and
  penetration-testing platforms); a human researcher
  marketplace is neither. The findings its engagements produce
  are ingestible by Core today — the marketplace and the
  coordination workflow are Extended. Registered from the
  fork's described function, not from a claim — the family
  claim did not fire because no family exists.

**Existing gaps explicitly gaining no claimant:**

- **Vulnerability scanners** (the Extended remainder of
  `vuln_management`) gains no claimant: the fork runs no scan;
  its researchers' output is finding-shaped, but the platform
  itself is a marketplace, and its description carries no
  scanning token.
- **Application security testing engines** gains no claimant —
  recorded explicitly because this is the easy place to cheat:
  the platform's *name* says "Security Testing", its description
  never does, and names are not evidence. What the description
  asserts in substance is booked once, under the new gap above,
  not double-booked here.
- **Detection engines and staffed SOC services** gains no
  claimant: "detect" is a verb in prose aimed at
  vulnerabilities, not a detection/SOC marker, and no
  threat/SIEM/incident token exists in the text.
- **Asset inventory** positions are unchanged: the family's
  absence was already a carried-Core note in the union spec,
  and "sensitive assets" / "internet-accessible assets" assert
  targets, not an inventory function.
- Every other Extended family is untouched: the newcomer's
  prose contains no token for any of them, claimed or otherwise
  (§2's whole-description absences).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  tables (the newcomer's empty table and the originals' tables
  exactly as shipped), the zero-claim set (all 25 families),
  verbatim census citations tagging nothing, registry fields as
  published, the near-miss pins, and the group totals (6 forks /
  13 claims / 5 of 6 claiming / the leading families at 3 of 6 /
  composition Low 4 + LI-SaaS 2) — see `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a disclosure-programme flow — a public-facing asset
  registered, a critical and an info researcher report ingested
  with severity moving the published score, the critical report
  triaged and assigned, posture reporting counts — and a bulk
  disclosure batch that enters atomically, links both findings
  to RA-5 at ingest, and rejects a malformed second batch whole.
  Both are carried-substrate cases: the fork claims no family,
  and the addendum claims none on its behalf.
- **Tests: 194 → 205, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the scoring line in
  `score_finding` (`src/cyber/store.py`) was patched to the
  severity-blind mutant `score = 3 * CRITICALITY_WEIGHTS[criticality]`
  (the exact line the shipped drill record names; asserted to
  occur exactly once before patching) and the full suite ran —
  **205 tests, exactly 32 failures**: the shipped drill's 31
  plus 1 from the new additions module
  (`test_additions.TestHackerOneSubstrate.
  test_researcher_findings_scored_triaged_and_counted`),
  tripping exactly as designed; a set comparison confirms no
  shipped-drill failure is missing from the mutant run.
  `store.py` was restored from the pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`, raw list in
  `scratch/additions_mutation_run.txt`, failure names in
  `scratch/additions_drill_failures.txt`.
