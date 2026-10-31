# Addendum — Analytics, CMMC L1: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:analytics-l1`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 10-function core,
and its control baseline are **unchanged**. This document records
what joined, what the newcomer claims under the group's existing
taxonomy, the core-delta decision for every claimed function, and
the updated union statement.

**Headline: forks spec'd 1 / 1; 3 new claims (group total 54 →
57); core delta — zero functions extended, `src/` byte-identical;
tests 136 → 149, all passing. 2 new gap functions** are named in
§5; 3 already-registered gaps gain claimants and 2 more gain
artifact-weight or by-substance entries, each labeled as such.
Two of the newcomer's three claims are **wording artifacts** of
the verbatim taxonomy and are recorded as artifacts, not rounded
up into substance (§2).

## 1. Membership and method

The 1 fork (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2017459185` | HP Inc. / Workforce Experience Platform Collaboration |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the original `scratch/extract.py`'s taxonomy via
  `ast` and asserts its literal copy of the (id, label, regex)
  triples equal to the original's before tagging** — the fixed
  24-function Analytics taxonomy was applied verbatim, not
  re-tuned for the newcomer. Same sentence splitting, same
  evidence rule (first matching sentence per family, stored
  verbatim), same sheet schema. The sheet is **appended** to
  `specs/specs.json` after the original 16, which are verified
  deep-equal to git HEAD, and the file is byte-preserved through
  the 16th sheet (the append is a pure 34-line insertion).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **LI-SaaS** (Certified), so it lands on the LI-SaaS side of the
  group's existing mix (now Low 6, LI-SaaS 11). LI-SaaS is
  FedRAMP's tailored **subset** of the Low baseline, so the union
  baseline — NIST SP 800-53 Rev. 5 Low ⇔ CMMC L1 — is unchanged
  (Merge Rules 1–2), inherited in full.
- The census starting point was verified, not trusted: the
  fork's **1 census citation** was re-checked against its own
  cached description and **verifies** as a verbatim substring —
  and it is exactly the sentence the taxonomy tags for
  `alerts_monitoring` (§2).
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty and its description is
  three sentences of own-product prose; only `service_desc` was
  matched, per house method. The census classification note is
  adopted as the group's own reading: *"Function is
  monitoring/analytics of collaboration technology, not
  collaboration itself."*

## 2. What the addition claims

**3 claims** for the 1 fork, under the verbatim taxonomy:

| Function | Additions claiming | Group total (17) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Alerts, monitoring & detection | 1 | 4 | Extended |
| Sharing & collaboration | 1 | 4 | Extended |
| Data transformation & preparation | 1 | 2 | Extended |

The fork: HP WXP Collaboration **3** claims. The full claim table
is pinned literally in `tests/test_additions.py`
(`EXPECTED_CLAIMS`):

- **`alerts_monitoring`** — "WXP Collaboration provides
  monitoring and analytics for collaboration and unified
  communication technology." This is the fork's one fully
  substantive claim: the product *is* a monitoring platform for
  collaboration technology.
- **`collaboration`** — fires on the product **name** in the
  first sentence ("…(WXP) Collaboration, formerly the Vyopta
  Platform…"). **Wording artifact, recorded not corrected:** the
  family's pattern is the bare token `collaborat`, so the name
  tags it; per the census note above, the fork's function is
  monitoring *of* collaboration technology, not a sharing or
  collaboration function. The claim stands at artifact weight.
- **`transform`** — fires on "**workplace transformation**" in
  the third sentence. **Wording artifact, recorded not
  corrected:** the family's pattern is the bare token
  `transform`; the sentence's substance is organizational change
  and technology migration, and the evidence sentence contains
  **no data wording at all** (pinned by test). The claim stands
  at artifact weight.

### Near-misses, itemized

The description is three sentences; the full per-sentence map is
`scratch/additions_sentence_map.json`. Substance that matches no
pattern:

- **"provides monitoring and analytics"** is not
  `statistics_ml`: the family requires machine-learning / AI /
  statistical / predictive wording, and none appears — "analytics"
  and "insights" are not its tokens. The platform's analytics
  substance lands in the monitoring claim and the §5 gaps, not in
  a statistics claim the prose does not make.
- **Monitoring with no live wording** is not `realtime`: no
  "real-time", "streaming", or "live" token appears, although the
  product monitors live collaboration environments in substance
  (counted by substance in §5).
- **"single-pane-of-glass, enterprise-wide visibility"** is not
  `visualization`: no dashboard / visualization / chart token
  appears. The visibility surface is dashboard substance with no
  dashboard word.
- **"across multi-vendor collaboration environments"** is not
  `connectors`: no connector / integration phrasing ("integrates
  with", "data sources") appears, although multi-vendor telemetry
  presupposes source integration in substance (counted by
  substance in §5).
- **"increase end user productivity"** is not `kpi`: no KPI /
  key-performance / performance-management wording.
- **"unified communication technology"** is not
  `media_analytics`: no image/video-analytics pattern fires; the
  UC surface is the monitored *subject*, gapped in §5 as
  telemetry, not as media analysis.
- **"technology migrations"** is not `ingest`, and nothing in
  the description carries reporting, query, export, API,
  governance, access-control, audit, encryption, archiving,
  geospatial, text/NLP, BI, or scheduling wording (all pinned as
  a checked absence set in the additions tests).

## 3. Core-delta decisions

Every family the addition claims is **Extended** in UNION-SPEC,
so no claim presupposes a records form or platform function the
build lacks:

| Claimed family (addition) | Disposition | Core delta |
|---|---|---|
| Alerts, monitoring & detection (1) | Extended — alerting/monitoring engines | **Carried** — no change |
| Sharing & collaboration (1) | Extended — collaboration surface | **Carried** — no change (and the claim is name-artifact weight) |
| Data transformation & preparation (1) | Extended — transformation engines | **Carried** — no change (and the claim is artifact weight) |

**Result: the core is unchanged.** `src/` is byte-identical to
the shipped build (all 10 modules hash-verified against the
pre-addition record after all work, the mutation drill included;
`src/analytics/query.py` SHA-256
`f15c9b8f528db4675de1437588aadf95a45067b0429bc1287a08ce6720faea2c`,
identical to the group's recorded pristine hash). The tier
baseline does not change: same tier by construction. The fork is
exercised against the substrate in the additions tests in its own
shape — collaboration-telemetry **aggregates** (per-vendor meeting
counts; no session content, no user data, per the category
discipline that records hold metadata and aggregates, never the
underlying datasets) ingested, grouped-queried, described,
charted, exported, and audited. No score of any kind is computed:
the fork's prose defines none, "productivity" wording
notwithstanding.

## 4. Updated union statement

The group now covers **17 forks** (16 original siblings + 1
remainder addition; Low 6, LI-SaaS 11), **57 claims** in total
(54 + 3), with **15 of 17** forks carrying at least one claim.
The merged build remains the same 10-function analytics platform
— ingest, dataset registry, query, descriptive statistics, SVG
visualization, reporting, export, REST API, RBAC hooks,
append-only audit — now spec'd against 17 marketplace offerings
instead of 16. The addition shifts no family's rank: reporting
and real-time remain joint-largest (8 each); the three moved
families (alerts/monitoring 3 → 4, collaboration 3 → 4,
transformation 1 → 2) are all Extended. The group's character
note: the union gains a unified-communications monitoring
platform whose taxonomy surface is thin *because its prose is
product prose* — one substantive claim (monitoring), two
name/phrase artifacts — which is the honest shape of this fork
under the group's fixed taxonomy, and is recorded as such rather
than padded.

## 5. Gaps — for the registry at ship

**New gap functions** (2):

- **Collaboration & unified-communications telemetry engine** —
  continuous telemetry collection from multi-vendor UC
  environments (endpoints, meeting and calling infrastructure),
  with end-user experience visibility and insights (HP WXP; its
  whole product). Named separately from the generic
  alerts/monitoring gap: that gap covers alerting and detection
  engines over data already in the platform, while this fork's
  surface is the upstream telemetry plane itself, which no
  registered gap names.
- **End-user experience & productivity analytics engine** —
  experience measurement and productivity insight over UC
  telemetry (HP WXP, by substance: "insights … to improve IT
  efficiency, increase end user productivity"). No taxonomy
  family claims it (the `statistics_ml` and `kpi` patterns did
  not fire, §2), and no score is defined by the prose or
  computed here; the engine is the gap.

**Existing gaps gaining claimants:**

- **Alerts, monitoring & detection engines** — +1 claimant: HP
  WXP (its substantive claim).
- **Proprietary-source connectors** — +1 **by substance**:
  multi-vendor collaboration environments presuppose UC source
  integration; the `connectors` family claim did not fire (no
  integration phrasing), recorded in §2.
- **Real-time & streaming analytics** — +1 **by substance**:
  continuous monitoring of live collaboration environments; the
  `realtime` claim did not fire (no live/real-time wording),
  recorded in §2.

**Artifact-weight entries (recorded, not counted as substance):**

- **Sharing & collaboration** gains the fork as a claimant at
  **artifact weight only** — the claim fires on the product name;
  the census and this addendum both record the function as
  monitoring *of* collaboration technology.
- **Data transformation & preparation** gains the fork as a
  claimant at **artifact weight only** — "workplace
  transformation" is organizational-change prose; no data
  transformation function is asserted, and no gap enlargement is
  claimed on its strength beyond this note.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  position, membership against `remainder.json`, the literal
  per-fork claim table, verbatim evidence, the census citation,
  the near-miss absence set (with trigger phrases proven present
  in the description), the two wording-artifact pins, and the
  combined group totals (see `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests: UC telemetry aggregates ingested with the
  metadata-only registry shape, per-vendor totals by grouped
  query, `describe` statistics over the minutes column, a
  standalone SVG chart and CSV export from one query result, and
  the audit trail across ingest / query / describe by the three
  demo identities.
- **Tests: 136 → 149, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the `avg` aggregation
  in `src/analytics/query.py` was patched to return the bare sum
  in both places an average is computed (the `_aggregate` avg
  branch and `describe`'s mean) and the full suite ran — **149
  tests, 13 failures**: the original drill's 12 (negative control
  ×4, describe ×5, query ×2, service ×1) plus exactly 1 from the
  new additions module (the substrate case's `describe` mean
  assertion), tripping exactly as designed. `query.py` was
  restored from the pre-mutation copy and verified SHA-256-
  identical to the shipped pristine hash; the suite re-ran green.
  Recorded in `tests/README.md`.
