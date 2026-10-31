# Addendum — Analytics, CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:analytics-l2`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 10-function core,
and its control baseline are **unchanged**. This document records
what joined, what the newcomer claims under the group's existing
taxonomy, the core-delta decision for every claimed function, and
the updated union statement.

**Headline: forks spec'd 1 / 1; 2 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 136 → 147, all
passing.** The newcomer's named function is the group's #4 family
(Visualization & dashboards, **Core**); its second claim
(Sharing & collaboration, Extended) fires inside its own service
catalogue and is recorded at catalogue weight in §2. **4 new gap
functions** are named in §5, all fork excess from that catalogue;
no already-registered gap gains a counted claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1508127183` | NetComm / Beacon |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the original `scratch/extract.py`'s `TAXONOMY`
  literal via `ast` (parsed, never executed, never re-typed)**
  before tagging — the taxonomy was applied verbatim, not re-tuned
  for the newcomer. Same sentence splitting, same evidence rule
  (first matching sentence per family, stored verbatim, truncated
  at 400 characters exactly as the original pass), same sheet
  schema. The sheet is **appended** to `specs/specs.json` after
  the original 128, which are byte-for-byte untouched (verified
  deep-equal to git HEAD, and the file re-serializes byte-identically
  for the original entries; the append is a pure +29-line insertion).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **Moderate** / Certified / SaaS, so the group stays single-tier
  and the L2 baseline is inherited in full (Merge Rules 1–2),
  unchanged.
- The census starting point was verified, not trusted: the fork's
  **1 census citation** ("NetComm offers a variety of cloud-based
  services through Beacon, NetComm's data analytics toolset that
  allows users to create customized dashboards … including:")
  re-checks as a verbatim substring of the fork's own cached
  description — **1 / 1 verifies**.
- **No exclusion trap applies to the newcomer.** The record's
  `certified_services` field is empty and no "not authorized"
  segment exists in the description (asserted in the extractor).
  Only `service_desc` was matched, per house method. The bullet
  catalogue inside the description is the fork's **own** offered
  services ("NetComm offers a variety of cloud-based services
  through Beacon … including:"), not a third-party hosted-applications
  catalogue, so the hosted-catalogue exclusion precedent does not
  apply; the catalogue's claim weight is adjudicated in §2 instead.

## 2. What the addition claims

**2 claims** for the 1 fork. Claim counts per family for the
addition, with the group's combined count (original 128 +
addition = 129 forks) alongside:

| Function | Addition claiming | Group total (129) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Visualization & dashboards | 1 | 34 | **Core** — charts & report bundles |
| Sharing & collaboration | 1 | 22 | Extended |
| (all other 22 families) | 0 | — | as in UNION-SPEC |

The full claim table is pinned literally in
`tests/test_additions.py` (`EXPECTED_CLAIMS`).

**The substantive claim — `visualization`.** The fork is, in its
own words, "NetComm's data analytics toolset that allows users to
create customized dashboards tailored to an organization's or
agency's particular needs", and its closing bullet is "Data
Visualization and Dashboarding". The evidence sentence is the
description's second sentence (the census citation is its lead-in).
This is the toolset's named function, and it is a Core family.

**The catalogue-weight claim — `collaboration`.** The family's
only match in the description is "online collaboration and
dashboard tools" inside the bullet service catalogue. The census
classifier's own note reads: "Named toolset is data
analytics/dashboarding; other listed items are a service
catalogue." The claim **stands** under the verbatim taxonomy —
the catalogue lists the fork's own offered services, and the
taxonomy is the group's law — but it is recorded at **catalogue
weight**: it is not the toolset's function, and per the
artifact-weight precedent it is **not counted** as an enlargement
of the sharing & collaboration gap in §5. Both claims carry the
same evidence string (the 790-character second sentence, truncated
to 400 characters by the extractor's standing rule); both matching
tokens — "customized dashboards" and "online collaboration" —
fall inside the kept window, verified by test.

### Near-misses, itemized

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`; the pins are in
`tests/test_additions.py`):

- **Statistical / predictive / ML & AI analysis** — "Improved
  access to and analysis of complex data" is the fork's only
  analysis wording; "analysis" alone matches no alternative (no
  statistical / predictive / forecast / ML / AI wording anywhere).
- **Scheduling & workflow automation** — "e-workflows" is not
  "workflow automation", and "Automated" in the catalogue modifies
  the back-office tools (HR, finance, property management), not
  workflow / report / process.
- **Access control & authentication** — "Standards & best
  practices for security & privacy management in the cloud" names
  no RBAC / SSO / authentication / access-control wording.
- **Connectors & source integration** — "Beacon leverages the
  Amazon Web Services GovCloud region FedRAMP moderate cloud
  Infrastructure as a Service (IaaS)" is platform prose; no
  connector or integrates-with wording (it is also the fork's
  hosting statement — this build inherits no AWS posture from it).
- **Data governance, catalog & metadata** — sentence 1's "custom
  information management software solutions" is not a governance
  alternative (no governance / catalog / metadata / lineage /
  data-quality wording).
- **Data storage / warehouse / lake** — no warehouse / lake /
  store / storage / repository / database wording anywhere; the
  toolset describes no data store of its own.
- **Reporting** — no "report" token appears anywhere in the
  description, despite dashboarding being claimed; in this build
  dashboard composition rides Core 5/6 regardless (see §3).
- **Query & search, API access, KPI & performance management,
  Business intelligence / self-service** — no SQL / query / search
  wording; no API wording; "help clients meet their organizational
  goals" is not KPI / scorecard / performance-metrics wording;
  "data analytics toolset" is not business-intelligence /
  self-service wording.

## 3. Core-delta decisions

| Claimed family (addition) | Disposition | Core delta |
|---|---|---|
| Visualization & dashboards (1) | Core 5 (Visualization) + Core 6 (Reporting) — a customized dashboard is a chart / report composition over ingested datasets | **Carried** — no change |
| Sharing & collaboration (1) | Extended (UNION-SPEC ranking row 7) | **Carried as a gap** — no core change; not counted as a gap enlargement (§5) |

**Result: the core is unchanged.** No function the fork claims
presupposes a records form or computation the build lacks:
dashboard composition is exercised against the shipped core by the
additions substrate case (grouped query → standalone SVG chart →
titled HTML report bundle). `src/` is byte-identical to the
shipped build (all 10 modules verified hash-equal to git HEAD
after all work, the mutation drill included; `src/analytics/query.py`
SHA-256 `f15c9b8f528db4675de1437588aadf95a45067b0429bc1287a08ce6720faea2c`).
The tier baseline does not change: same tier by construction. The
category discipline holds unchanged: the build's dataset registry
holds metadata, schema, and rows the operator ingests — analytics
records and checksums about datasets, never a computed score; the
fork's prose defines no score and none is computed.

## 4. Updated union statement

The group now covers **129 forks** (128 original siblings + 1
remainder addition), **422 claims** in total (420 + 2), with
**116 of 129** forks carrying at least one claim. The merged build
remains the same 10-function analytics substrate — ingest, dataset
registry, query & search, descriptive statistics, visualization,
reporting, export, API access, RBAC hooks, append-only audit — now
spec'd against 129 marketplace offerings instead of 128. The
group's character barely moves: the newcomer claims the group's
core surface (dashboards) rather than its long tail, and its
remaining described surface is a back-office service catalogue
that belongs to other categories (see §5).

## 5. Gaps — for the registry at ship

**New gap functions** (4), all fork excess from the newcomer's
service catalogue — surfaces the fork's own description asserts
that fall outside this group's taxonomy entirely:

- **Automated back-office service tools** (HR, finance, and
  property-management automation) — Beacon catalogue excess
- **Digital signature engine** — Beacon catalogue excess
- **E-workflow tooling** (business-process workflows) — Beacon
  catalogue excess; distinct from the group's Extended
  *scheduling & workflow automation* family, which covers
  scheduled analytics jobs and report automation
- **Mobile client capabilities** — Beacon catalogue excess

**Existing gaps gaining claimants:**

- **Sharing & collaboration** — explicitly gains **no counted**
  claimant: the addition's collaboration claim is catalogue
  weight (§2), recorded here rather than counted, per the
  artifact-weight precedent.
- No other registered gap gains a claimant. (Visualization is a
  Core family, not a gap.)

## 6. Verification

- Spec integrity is pinned by tests: sheet count and position,
  membership against `remainder.json`, the literal claim table,
  the zero-claim family set, verbatim evidence with both matching
  tokens inside the evidence window, the census citation, and the
  near-miss pins (see `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same file: an agency-services dataset is ingested, grouped, and
  composed into a customized dashboard (standalone SVG bar chart
  inside a titled HTML report bundle), and the dashboard's
  averages are asserted to be means (grouped avg 15 over
  (10, 20); describe mean 20 over (10, 20, 30)).
- **Tests: 136 → 147, all passing** (both discovery modes).
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `src/analytics/query.py`
  was patched so both the `avg` aggregate and `describe`'s mean
  return `sum(numbers)`, and the full suite ran — **147 tests,
  exactly 13 failures**: the shipped drill's 12 (describe ×5,
  negative control ×4, grouped/aggregate avg ×2, service describe
  ×1) plus exactly 1 from the new additions module (the Beacon
  dashboard-statistics case), tripping on the mutant exactly as
  designed. `query.py` was restored from the pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
