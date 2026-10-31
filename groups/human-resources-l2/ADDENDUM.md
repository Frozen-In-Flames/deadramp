# Addendum — Human Resources, CMMC L2: the 3 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 3
previously uncategorized forks of remainder build unit
**`addition:human-resources-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 12-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomers claim under the group's
existing taxonomy, the core-delta decision for every claimed
function, and the updated union statement.

**Headline: forks spec'd 3 / 3; 11 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 77 → 89, all
passing; two of the group's six named absences are retired** —
leave & time-off and time & attendance, which stood at 0 of 4 in
the original spec, are asserted in substance by one newcomer's own
prose (Paycheck 8), with the consequences worked out in §3.
**6 new gap functions** are named in §5, and 4 already-registered
gaps gain claimants or substance.

## 1. Membership and method

The 3 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1834348080` | GDC Integration, Inc. / General Support System (GSS) |
| 2 | `FR2002757173` | Government Retirement & Benefits, Inc. / GRB Platform |
| 3 | `FR1818240234` | Perceptyx / Perceptyx Insights Platform |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which parses the original `scratch/extract.py`'s taxonomy via
  `ast.literal_eval` (parsed, never executed) and applies it
  verbatim — same sentence splitting, same evidence rule (first
  matching sentence per family, stored verbatim, 400-char
  truncation), same sheet schema. The group's `scratch/` is
  gitignored, so no git-HEAD copy of the taxonomy exists to diff
  against; verbatim application is instead **proven end-to-end**:
  before tagging any newcomer, the extractor re-runs the parsed
  taxonomy over the original 4 forks' cached descriptions and
  asserts it reproduces their shipped claim tables **exactly**
  (function ids and evidence strings, all 38 claims). Any pattern
  drift would fail that reproduction. The 3 sheets are **appended**
  to `specs/specs.json` after the original 4, which are
  byte-for-byte untouched (verified by deep-equality against git
  HEAD and by byte-preservation through the fourth sheet's closing
  brace).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID; the
  descriptions used are asserted identical to the census cache
  (`remainder/uncovered.json`). All 3 descriptions were present;
  no live fetching. All 3 are FedRAMP **Moderate**, FedRAMP
  Certified, SaaS on Government Community Cloud, so the group
  stays single-tier and the L2 baseline is inherited in full
  (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all
  **3 census citations** for these forks were re-checked against
  the forks' own cached descriptions and **3 / 3 verify** as
  verbatim substrings. Two of the three also became claims (GRB's
  and Perceptyx's citations are their single claims' evidence);
  GDC's citation (its opening human-capital sentence) tags no
  family — verification is not a claim, stated plainly.
- **No exclusion trap applies to the newcomers.** None of the 3
  records carries a hosted-services block: every record's
  `certified_services` field is empty (asserted in the extractor).
  Only `service_desc` was matched, per house method.

## 2. What the additions claim

**11 claims** across the 3 forks; all 3 carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 4 + additions = 7 forks) alongside:

| Function | Additions claiming | Group total (7) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Reporting, dashboards & analytics | 2 | 4 | **Core** — reporting over the records (Core 10); visualization engines Extended |
| Benefits & retirement administration | 2 | 3 | **Core** — benefits & retirement records (Core 8); calculator Extended |
| Performance management | 1 | 3 | **Core** — review cycle records (Core 7) |
| Personnel actions, forms & case management | 1 | 3 | **Core** — personnel action & case records (Core 9) |
| Workforce planning & resource management | 1 | 3 | Extended — planning analytics/models; position records carry the org side |
| AI & workflow automation | 1 | 3 | Extended — AI matching and automation engines |
| Audit & compliance review | 1 | 3 | **Core** — audit log (Core 12) |
| New-hire onboarding & entrance-on-duty | 1 | 2 | **Core** — lifecycle case records (Core 6) |
| Awards & recognition | 1 | 2 | **Core** — as a personnel-case kind (Core 9) |

Per-fork claim counts: GDC Integration GSS **9**, GRB Platform
**1**, Perceptyx **1**. The full per-fork table is pinned literally
in `tests/test_additions.py` (`EXPECTED_CLAIMS`).

The group's center of gravity moves: reporting & analytics (4 of
7) displaces talent acquisition (3 of 7) as the largest family,
and benefits & retirement — the original union's thinnest Core
family at 1 of 4, flagged thin — reaches 3 of 7, gaining in GRB a
substantive specialist whose entire product is the family's
function. The additions are **post-hire** tooling: not one of the
eleven claims touches the hiring chain (classification →
announcement → application → assessment → panel → referral) that
dominates the original union.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **GDC Integration GSS** — Its Labor-Employee Relations
  Information System (LERIS) is literally a labor-relations
  system, yet `labor_relations` does not fire: the text writes
  "Labor-Employee Relations" and "labor/employee relations
  specialist", never the taxonomy's contiguous phrase "labor
  relations" (the `personnel_actions_cases` claim rests on
  LERIS's "case management" in the same sentence; LERIS's EEO
  case-manager audience has no family at all). "role management"
  (Connect HR) is not `access_control` ("role-based" / "granted
  access" required). The vendor's *name* contains "Integration",
  but the description body contains no `integrat\w+` token, so
  `integrations` does not fire on a name — the name-only
  precedent. FedChart "visualizes an agency's organizational
  structure, positions, and workforce costs" is not
  `position_classification` (no classification / position
  description / position management phrase). The opening census
  sentence ("Federalized SaaS Human Resource Applications …
  human capital functions across the employee lifecycle") tags
  nothing: "human capital" and "employee lifecycle" are no
  family's phrases.
- **GRB Platform** — The "flexible bi-directional interface used
  to communicate with an Agency's payroll/HRIS system, third
  party benefits providers, and any outside parties" is not
  `integrations`: "interface" is not an `integrat\w+` token. The
  interface is connector *substance* and is counted as such in
  §5, but no claim fires. A complete benefits-administration
  platform whose 617-character description contains no reporting,
  audit, case-management, or access phrase claims exactly the
  one family it names.
- **Perceptyx** — "performance improvement services" is not
  `performance_management`. The Develop Service's "Multi-rater
  feedback" matches no evaluation family (`panel_review` requires
  SME-panel wording; `hiring_assessments` requires assessment
  phrasing) — feedback *records* would be Core-5-shaped, but no
  claim fires and none is recorded. "real-time technology" is
  not `ai_automation`; no AI or automation wording appears.
  Perceptyx's actual function — employee engagement surveys and
  listening — has **no taxonomy family**: exactly the IdeaScale
  shape from the Collaboration L2 addition, recorded as a gap in
  §5 rather than forced into a family.

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the group's
law, applied verbatim:

- **GDC, `benefits_retirement`** fires on the *generic* phrase
  "leverage the benefits of single sign on" in the Connect HR
  sentence. No benefits administration is asserted there; the
  claim stands at artifact weight. The family's substantive
  addition claimant is GRB, and §3's disposition does not depend
  on GDC's artifact.
- **GDC, `awards_recognition`** first-matches the ePM sentence's
  "performance and awards laws" (compliance with awards *law*).
  The substantive awards surface — eTracker's "Awards
  Processing" over SF-52/SF-50 actions — sits later in the same
  description and is what §3 assigns to Core 9's award kind.
- **GDC, `ai_automation`** fires via `automat\w+` on FedChart's
  "automates the creation, maintenance, and updating of
  organizational charts". The description contains **no AI
  wording at all** (no "artificial intelligence", no standalone
  AI token — pinned in tests). This is the UNION-SPEC caveat-3
  precedent verbatim: FedHire's onboarding claim likewise rests
  on "automates entrance-on-duty processing". Automation is
  claimed; AI is not asserted by this fork, and §5 records the AI
  engines gap as gaining **no** claimant from it.
- **GDC, `audit_compliance`** fires on the compliance-*outcome*
  phrase "maintaining compliance with performance and awards
  laws" in the ePM sentence; no "audit" token appears in the
  evidence (the UNION-SPEC caveat-5 precedent, Eightfold's
  "meet compliance requirements"). GDC's reporting prose
  (FedViews "in compliance with OPM requirements") is the same
  weight. The claim stands; Core 12's substance in the enlarged
  group still rests on FedHire, as before.
- **GDC, `reporting_analytics`** first-matches the Paycheck 8
  sentence ("tracking and reporting time, attendance, and
  leave") — a real reporting assertion, but its subject is the
  time & attendance surface of §3, not workforce reporting. The
  family's GDC substance beyond that sentence is FedLens
  ("automated reports, trend analysis, and predictive
  analytics") and FedViews (FEVS reporting), recorded in §5.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Reporting & analytics (2) | Core 10 — counts/summaries over the substrate | **Carried** |
| Benefits & retirement (2) | Core 8 — enrollment & retirement-case records | **Carried** — GRB's records are the shipped form; its administration depth is a gap (§5) |
| Performance management (1) | Core 7 — review cycle records | **Carried** |
| Personnel actions & cases (1) | Core 9 — case records | **Carried** |
| Awards & recognition (1) | Core 9 — award case kind | **Carried** |
| Onboarding (1) | Core 6 — lifecycle cases with task checklists | **Carried** — eForms' form-population side is the already-Extended document assembly (§5) |
| Audit & compliance (1) | Core 12 — append-only audit log | **Carried** |
| Workforce planning (1) | Extended in UNION-SPEC — planning analytics/models | **Carried as Extended** — FedChart's engine is a new gap (§5); position records already carry the org-structure side |
| AI & automation (1) | Extended in UNION-SPEC — engines | **Carried as Extended** — no AI asserted; see the artifact note in §2 |

**The retired absences, decided plainly.** UNION-SPEC named six
absences at 0 of 4 *because unclaimed* — "not built, not a gap".
The additions change two of them, and the absence probes were
re-run over the newcomers' prose (probe results pinned in tests;
full output in `scratch/additions_absence_probes.json`):

- **Leave & time-off — RETIRED.** GDC's Paycheck 8 is a leave
  product in its own words: "tracking and reporting time,
  attendance, and leave (including VLTP and FLMA)" and "Leave
  balances" (the description's "FLMA" spelling stands as
  written). The leave probe fires on 2 of GDC's sentences.
- **Time & attendance — RETIRED by substance.** The original
  absence probe (`time and attendance|timesheet`) does **not**
  fire on GDC's prose — Paycheck 8 writes "time, attendance"
  with a comma, and the probe requires the conjunction. Both
  facts are recorded and pinned: the literal probe still reads
  zero, and the substance is unmistakably time & attendance
  tracking. An absence that survives only on a comma is not an
  absence.
- **Consequence, stated once:** retiring an absence is not
  adding a Core function. No taxonomy family for leave or time &
  attendance exists, no original sibling presupposed their
  records, and the family that did fire over the Paycheck 8
  sentence (`reporting_analytics`) is carried by Core 10. The
  time, attendance & leave *tracking* surface therefore enters
  as a **new Extended gap** (§5) for the final batch — the
  category now demonstrably contains the function, and the
  build's silence about it is a gap, not a finding.
- **Payroll — absence stands, wording updated.** The word
  "payroll" now appears exactly once across all 7 descriptions:
  inside GRB's interface sentence, naming an *external* system
  ("an Agency's payroll/HRIS system") the platform communicates
  with. (The original union's only trace was likewise external —
  the NFC named as an integration target.) No fork claims a
  payroll function; the absence stands as a function, and the
  interface itself is connector substance under §5.
- **Policy acknowledgements, background checks, salary /
  compensation administration — absences stand.** The probes
  (`polic|acknowledg`; `background check|background
  investigation`; `salary|compensation`) return zero hits across
  all 3 newcomers, so all three remain at 0 of 7. (GDC's
  "workforce costs" is not compensation administration wording,
  and no pattern is stretched to make it so.)

**Result: the core is unchanged.** No function the 3 claim
presupposes a records form the build lacks. `src/` is
byte-identical to the shipped build (`src/hr/store.py` SHA-256
`ec34ab5e55f81b88a027aca6a29d024e18786f4791646dca7213b56f0a1061f0`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction. Person records remain opaque-reference only; no
newcomer's claims introduce any field capable of holding real
PII, and the substrate cases run under the shipped privacy
shapes, pinned by the suite's existing privacy tests.

## 4. Updated union statement

The group now covers **7 forks** (4 original siblings + 3
remainder additions), **49 claims** in total (38 + 11), with
**7 of 7** forks carrying at least one claim. The merged build
remains the same 12-function HR records substrate — persons,
positions, vacancies, applications, evaluations, lifecycle
cases, performance cycles, benefits & retirement records,
personnel cases, counts-only reporting, RBAC, append-only audit
— now spec'd against 7 marketplace offerings instead of 4. The
group's character broadens: the original union was a
hiring-and-records group (its own spec's words) whose center was
talent acquisition; the additions are post-hire operations —
appraisal, benefits administration, personnel actions, workforce
reporting — plus the category's first survey-listening product
and its first time & attendance product, both present as gaps
rather than claims. Two absences are retired, one absence's
wording is updated, and the substrate/engine split is unchanged:
every engine the newcomers operate is named in §5, and nothing in
the build computes a score, a benefit amount, or a leave balance.

## 5. Gaps — for the registry at ship

**New gap functions** (6):

- **Time, attendance & leave tracking engine** — GDC (Paycheck
  8: time-entry pre-edits under agency business rules, corrected
  T&As, leave balances incl. VLTP/FMLA). Retires the leave &
  time-off and time & attendance named absences (§3).
- **Organizational chart generation & maintenance automation**
  — GDC (FedChart: automated creation, maintenance, and updating
  of org charts from federal HR data, adhering to
  agency-specific business rules).
- **Employee engagement survey & listening platform** — Perceptyx
  (point-in-time and lifecycle surveys, always-on listening,
  crowdsourced dialogue, multi-rater feedback, diagnostic
  reporting and action-planning modules). The fork's whole
  function; no taxonomy family exists for it (§2).
- **Federal retirement & benefits administration platform
  depth** — GRB fork excess beyond Core 8 records:
  specialist / manager / employee administration tooling over
  the records, HRLoB-aligned workflows. Distinct from the
  existing *retirement benefits calculator* gap: GRB asserts
  administration, not calculation.
- **Employee self-service portal & HR dashboard** — GDC
  (Connect HR: single-sign-on dashboard, role management,
  collaboration, communication, business intelligence, document
  management front-end).
- **Uniform allowance request processing** — GDC (UNAW:
  processing, tracking, and approval of uniform allowance
  requests online). Fork excess; no taxonomy family.

**Existing gaps gaining claimants or substance:**

- **Workforce planning & resource-management analytics/models**
  (UNION-SPEC long tail) — +1 claimant: GDC (FedChart claim),
  and +substance: FedLens (diagnostics, snapshots, predictions;
  benchmarking against OPM standards; predictive analytics) and
  FedViews (automated FEVS reporting, trend analysis, workforce
  planning).
- **Integration connector engines** — +1 by substance: GRB (the
  bi-directional payroll/HRIS and third-party benefits-provider
  interface; the `integrations` claim itself did not fire,
  recorded in §2).
- **Document & template assembly engines** — +1 by substance:
  GDC (eForms enrollment-form management; eTracker's SF-52 /
  SF-50 personnel-action form processing).
- **AI talent intelligence & matching engines** — explicitly
  gains **no** claimant from the additions: GDC's
  `ai_automation` claim is automation wording with no AI
  asserted (§2), and nothing in the 3 descriptions presupposes
  a matching model.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim family set (16 families), verbatim
  evidence, the census citations (3/3), the near-miss pins, the
  wording-artifact pins, and the absence-update pins (see
  `tests/test_additions.py`).
- The taxonomy's verbatim application is proven by the
  extractor's reproduction check: the original 4 forks' shipped
  claim tables (38 claims, ids + evidence) are reproduced exactly
  from the parsed taxonomy before any newcomer is tagged.
- Every addition fork is exercised against the substrate in the
  same tests: an onboarding lifecycle case derived through
  in_progress to complete, a completed performance cycle with a
  verbatim outcome label, and personnel-action / award /
  labor-relations case records (GDC); retirement-case and
  benefit-enrollment records moved to active, with employee
  scope enforced (GRB); counts-only reporting over lifecycle,
  performance, and case records with a recursive no-score-key
  scan and the employee report denial (Perceptyx).
- **Tests: 77 → 89, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the complete branch
  of `HrStore._derive_case_status` in `src/hr/store.py` was
  patched (`return "complete"` → `return "in_progress"` under the
  all-done/waived condition) and the full suite ran — **89
  tests, exactly 7 failures**: the original drill's 5
  (lifecycle add-task, lifecycle derivation progression,
  negative control canonical case, reporting derived status,
  service full flow) plus 2 from the new additions module (the
  GDC onboarding derivation case and the Perceptyx reporting
  case), which trip on the mutant exactly as designed.
  `store.py` was restored from the pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
