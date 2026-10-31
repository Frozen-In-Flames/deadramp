# Addendum — Education & Training, CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:education-training-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 10-function
core, its core-boundary decisions, and its Moderate control baseline
are **unchanged**. This document records what joined, what the
newcomer claims under the group's existing taxonomy, the core-delta
decision, and the updated union statement.

**Headline: fork spec'd 1 / 1; 4 new claims — the group total moves
43 → 47; core delta — zero functions extended, `src/`
byte-identical; tests 65 → 79, all passing; the group's signature
compliance-derivation drill re-run in this tree (exactly 9
failures under mutation).** All four claims are Core families, and
the union spec's floor **survives**: no fork in the enlarged group
has zero claims (9 of 9 claim). **No new gap functions** are named
in §5 — the newcomer's every described function is claimed, Core,
or already in the union's Extended set — and 3 already-registered
gaps gain a claimant, one of them in substance only (online
proctoring, for which this taxonomy has no family).

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2135637226` | Pearson VUE / Pearson Federal Cloud System |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact 21 (id, label, regex)
  triples** — the taxonomy was applied verbatim, not re-tuned for
  the newcomer. The original extractor carries **no CORRECTIONS
  literal**: its six wording-artifact corrections
  (`scratch/ARTIFACTS.md`) were applied by tightening the patterns
  themselves, so the shipped patterns are the corrected taxonomy —
  asserted in the extractor. Same sentence splitting, same
  evidence rule (first matching sentence per family, stored
  stripped and truncated past 400 chars), same 14-key sheet
  schema, before tagging the newcomer the extractor **reproduces
  the original 8 forks' shipped sheets whole from the raw cache**
  (deep-equal, not just claim tables) and asserts the family
  counts against `scratch/function_counts.json` (43 claims). The
  sheet is **appended** to `specs/specs.json` after the
  originals, which are deep-equal to git HEAD and byte-preserved
  through the eighth sheet's closing brace (asserted in the
  extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **Moderate / Certified** (SaaS, Public Cloud), so the group
  stays single-tier and the Moderate baseline is inherited in
  full (Merge Rules 1–2), unchanged. In the source the fork was
  **uncategorized** (`business_categories` empty; `forks.json`
  category "Uncategorized (none in source)"); the census proposed
  Education & Training, recorded on the sheet as the DeadRamp
  category. Category boundary, kept: this is the Education &
  Training group — nothing was imported from Learning
  Management's separate taxonomy, and nothing here was re-filed
  under it.
- The census starting point was verified, not trusted — and the
  verification itself has a twist, recorded in §2: of the fork's
  **2 census citations**, one verifies as a strict verbatim
  substring of the cached description and one verifies only
  whitespace-normalized, because the source text carries a line
  break inside that sentence.
- **No exclusion applied.** The fork's record carries **no**
  `certified_services` block (empty, asserted in the extractor),
  and the FedHIVE trap has no analogue here: the description's
  third sentence enumerates the fork's **own** subsystems inside
  its own FedRAMP boundary — the Athena Browser/Desktop test
  drivers, the OnVUE proctoring platform, and IntelliVUE
  reporting are Pearson VUE's own components of this very
  offering. That is an in-scope enumeration of its own function
  prose, not a catalogue of third-party hosted applications and
  not a scope-exclusion segment. Nothing was excluded; matched
  text is the full text, and raw hits equal surviving claims
  (4 = 4), with zero wording-artifact corrections. Only
  `service_desc` was matched, per house method.

## 2. What the addition claims

**4 claims**, all substantive and all Core families — no wording
artifacts, no correction applied or needed:

| Family | Evidence (verbatim, first matching sentence) |
|---|---|
| `enrollment_registration` — Enrollments & candidate registration | "Pearson VUEs Pearson Federal Cloud System securely delivers assessments to registered testing candidates for over 450 assessment programs." |
| `assessments` — Assessments & testing — delivery & administration | (same sentence) "…securely delivers assessments to registered testing candidates…" |
| `scheduling` — Scheduling of training & assessment sessions | "The system is built on Microsoft's Azure Commercial Cloud infrastructure-as-a-service (IaaS) [line breaks in source] Pearson VUE's FedRAMP boundary includes candidate registration and scheduling systems; candidate testing on Athena Browser Edition (A-BE) or Athena Desktop (A-DE) test drivers; the OnVUE online proctoring platform; and reporting systems, including IntelliVUE." |
| `reporting_analytics` — Reporting, dashboards & analytics | (same sentence) "…and reporting systems, including IntelliVUE." |

The per-sentence map is `scratch/additions_sentence_map.json`
(3 sentences under the group's splitting rule; sentence 1 tags 2
families, sentence 2 tags 1 already-claimed family, sentence 3
tags 3, of which 2 are new to this fork).

**The census twist, stated plainly.** Citation 1 ("Pearson VUEs
Pearson Federal Cloud System securely delivers assessments to
registered testing candidates for over 450 assessment programs.")
verifies as a strict verbatim substring — and **is** the
`enrollment_registration` / `assessments` evidence sentence.
Citation 2 ("Agencies and other government organizations can use
the Pearson Federal Cloud System to administer high stakes
assessments to potential job candidates.") does **not** verify
strictly: in the cached source text that sentence contains a
line break ("assessments\n to potential job candidates"), so it
verifies only after whitespace normalization. The census's
citation check was evidently whitespace-insensitive. Neither
citation is load-bearing — no claim rests on citation 2, and the
`assessments` claim rests on sentence 1, which precedes it —
but the accounting is pinned in `tests/test_additions.py`
exactly as measured, in both directions: a strictly verified
citation can be a claim's evidence, and a citation that fails
strict verification can still be a faithful quote modulo a line
break. Verification is not a claim, and non-verbatim is not
fabrication; each is recorded as what it is.

**What the claims do.** All four families are already Core
(enrollment/registration records, Core 2; assessment records,
Core 4; scheduling records, Core 7; reporting over the records,
Core 8), so the enlarged group needs no core extension — the
newcomer is a second instance of the group's testing pole (PSI
Gov Secure Cloud is the first): a candidate-facing assessment
platform whose records the substrate already holds. The claims'
engines — the Athena test-driver delivery engine, the OnVUE
proctoring engine, the IntelliVUE reporting engine — are
Extended and stay Extended (§5). Family counts move:
`enrollment_registration` 2 → 3 of 9, `assessments` 2 → 3,
`scheduling` 2 → 3, `reporting_analytics` 3 → 4.

### Near-misses, itemized

- **`course_catalog`** — "over 450 assessment programs" is a
  registry of programs in substance (and Core 1 holds program
  records), but the family's tokens are "course", "training
  program", "learning environment", "curriculum" — none appears
  ("assessment programs" is not "training program"). Stays 0 for
  this fork.
- **`certificates_credentials`** — Pearson VUE's real-world
  business is certification testing, and its candidates sit for
  certification exams; the description nevertheless contains no
  certification, credential, licensure, or certificate token at
  all (pinned by regex in the tests). Reputation is not evidence.
  Stays 0.
- **`hosting_platform`** — "built on Microsoft's Azure Commercial
  Cloud infrastructure-as-a-service (IaaS)" does not fire the
  family's PaaS-shaped pattern (platform-as-a-service / PaaS /
  multi-tenant / hosted-within / deployed-in), and the underlying
  Azure infrastructure is the fork's platform layer, which does
  not transfer to the build in any case (the merged build is a
  single-tenant reference deployment). Stays 0.
- **`learner_progress`** — the fork tests candidates; it does not
  describe tracking them: no readiness, progress, completion, or
  "tracking of" token. Stays 0.
- **`compliance_training`** — no "compliance" token anywhere.
  Stays 0.
- **`recruitment_workforce` / `talent_skills`** — "potential job
  candidates" is hiring-adjacent substance, but there is no
  recruit / hiring / hire / onboard token ("high stakes" is not
  "hire") and no talent / skills token. Both stay 0.
- **`content_media`** — the Athena "test drivers" are delivery
  software in substance; the family needs a content / recording /
  debriefing token and has none. The delivery engine is booked
  once, under the assessments Extended item in §5 — not
  double-booked here. Stays 0.
- **`access_control`** — "securely delivers" is adverbial
  platform prose, not an authorized-user or access-control
  phrase — the same artifact class as the original group's
  Acadis correction. Stays 0.
- **Whole-description absences** — no scoring/grading wording,
  no identity token, no notification/reminder token, no "api"
  substring, no "stream" substring, no authoring, data-services,
  simulation, AI/automation, performance, policy, career, or
  collaboration token. Seventeen of the twenty-one families stay
  at 0 for this fork, each on token-level evidence pinned in the
  tests.

## 3. Core-delta decision

| Family / substance (addition) | Disposition | Core delta |
|---|---|---|
| `enrollment_registration` (claimed) | Core 2 — enrollment & candidate registration records | **Carried** — no change |
| `assessments` (claimed) | Core 4 — assessment administration records; the delivery/test-driver engine is Extended per the union ranking | **Carried** — records only; engine is a gap (§5) |
| `scheduling` (claimed) | Core 7 — scheduling records | **Carried** — no change |
| `reporting_analytics` (claimed) | Core 8 — reporting over the records; dashboard/analytics engines Extended | **Carried** — records only; engine is a gap (§5) |
| Online proctoring (asserted in substance; no family in this taxonomy) | Extended — already registered as README gap 5 (remote proctoring & identity proofing) | **Gap** (§5) — gains a claimant in substance; not an extension |
| Azure / IaaS platform layer ("built on … Azure Commercial Cloud") | Platform note — the fork's hosting property; does not transfer | No delta — not a function |

**Result: the core is unchanged.** Every claimed family was
already Core, and the one substance with no family (proctoring)
was already a registered gap. `src/` is byte-identical to the
shipped build (all seven `src/learn/` module hashes identical
before and after this addendum's work, the mutation drill
included — e.g. `store.py` SHA-256
`f9c8ea1018db3d3ba10fc21bd00a7c592f4adf682d3a23e0fdc6a7417cbd3ffc`;
the full `src/` tree diff against HEAD is empty). The tier
baseline does not change: same tier by construction.

## 4. Updated union statement

The group now covers **9 forks** (8 original siblings + 1
remainder addition), **47 claims** in total (43 + 4), with
**9 of 9** forks carrying at least one claim — the union spec's
"no fork has zero claims" floor survives the addition, now
against a group whose thinnest member (Peraton NGCP, 2 claims)
is unchanged and whose newcomer claims 4. The merged build
remains the same education-and-training records substrate at the
Moderate baseline — course/program registry, enrollments and
candidate registrations, progress/readiness records, assessment
administration records with no scoring, credential records,
compliance assignments with status derived at read, scheduling
records, reporting over the records, RBAC, and the append-only
audit log — now spec'd against 9 marketplace offerings instead
of 8. The addition sharpens the group's testing pole: two of the
nine forks (PSI Gov Secure Cloud and Pearson Federal Cloud
System) are secure computer-based testing platforms, and the
families they share — registration, assessments, scheduling,
reporting — are exactly the families whose counts move. Nothing
about the substrate had to change to absorb a second testing
platform, which is what the original core-boundary decisions
predicted: the substrate holds the records; each vendor's
delivery, proctoring, and reporting engines sit on top as
Extended functions.

## 5. Gaps — for the registry at ship

**New gap functions: none.** Every function the newcomer
describes is either claimed above, already Core, or already in
the union spec's Extended set. Registering a new gap name for an
already-registered function would double-book it; the honest
accounting is the claimant list below.

**Existing gaps gaining claimants** (3):

- **Remote proctoring & identity proofing** (README gap 5) gains
  a claimant **in substance, for the proctoring half only**:
  the fork names "the OnVUE online proctoring platform" in its
  own words. This taxonomy has no proctoring family, so no claim
  fired and none is recorded; the engine remains Extended. The
  named-absence accounting changes accordingly and is stated
  plainly below. The identity-proofing half gains **no**
  claimant: the description contains no identity token.
- **Assessment delivery & test-driver engines** (Extended per
  the union spec's function ranking: "delivery engines and
  scoring Extended") gains a claim-backed claimant: the newcomer
  claims the `assessments` family, and its entire described
  function is delivery — assessments delivered to registered
  candidates through the Athena Browser Edition and Athena
  Desktop test drivers. The administration *records* are Core 4;
  the delivery engine remains Extended. The scoring half of that
  Extended item gains **no** claimant (see below).
- **Reporting / analytics engines** (Extended per Core 8) gains
  a claimant: the newcomer claims `reporting_analytics`, and its
  IntelliVUE is a named reporting system — an engine in
  substance. Reporting *over the substrate records* is Core 8;
  the engine remains Extended.

**Existing gaps explicitly gaining no claimant** — itemized,
because each was plausible:

- **Deterministic scoring & AI grading** gains **no** claimant:
  the fork delivers "high stakes assessments" but its
  description contains no score/grade wording (pinned in the
  tests). Stakes are not scoring.
- **Integrations & APIs** gains **no** claimant: the description
  contains no "api" substring at all (the original group's only
  hit was inside "Human Capital Management"; the newcomer does
  not repeat it). The named absence survives at 0/9.
- **Notifications & reminders** gains **no** claimant: no
  notification or reminder token; the absence survives at 0/9 —
  notable because the fork schedules test sessions, the natural
  companion function, without claiming reminders.
- **Course content authoring & delivery, media streaming**
  gains **no** claimant: no content or streaming token (the
  test drivers are booked once, under the delivery-engines item
  above).

**Named absences:**

- **Retired as a substance finding (proctoring half only):
  proctoring.** The union spec records proctoring & identity
  verification/proofing as a named absence, 0/8. For the
  enlarged group that no longer holds in substance for
  proctoring: 1 of 9 descriptions asserts an online proctoring
  platform in its own words. It **survives as a claims absence**
  — 0/9 forks claim proctoring, because no family exists to
  claim it under — and the gap above carries the claimant.
  Identity verification/proofing remains absent in both senses
  (0/9 in substance and in claims; no identity token in any of
  the 9 descriptions' newcomer, and the original 8 stand as
  recorded).
- **Surviving, unchanged:** deterministic scoring/grading,
  notifications/reminders/alerts, audit logging in descriptive
  text, API/integrations, video/media streaming, course content
  authoring, explicit due-date/deadline/expiry wording, and
  explicit completion/transcript wording — each still at 0/9 in
  the enlarged group's descriptions (the newcomer's description
  contains none of their tokens; pinned in the tests).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the original 8
  forks' literal claim counts (43), the newcomer's literal
  four-claim table with its pinned evidence sentences, the group
  totals (47 claims; zero zero-claim forks; the four family
  counts), registry fields as published, the verbatim
  description, the census citation accounting (one strict, one
  whitespace-normalized-only — pinned as measured), the
  no-exclusion pin (empty `certified_services`), the proctoring
  accounting (substance present, no family anywhere), and the
  near-miss token pins — see `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a candidate testing flow (assessment program registered as a
  `program` registry entry, a candidate registration, a
  scheduled assessment session, an assessment administration
  record bound to the session holding a verbatim item response
  and no score/grade field, read back through reporting), and a
  compliance case in which a past-due assignment over the
  program reads `overdue` at read and `completed` after a
  completed progress record.
- **Tests: 65 → 79, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree. The overdue branch of
  `LearnStore._derive_status` in `src/learn/store.py` (`return
  "overdue"` under `if as_of_date > due:` — the named line
  occurs exactly once; count asserted, patch scoped) was patched
  to `return "current"`: the full suite ran — **79 tests,
  exactly 9 failures**: the shipped drill's 8 plus 1 from the
  new additions module
  (`test_pearson_candidate_compliance_derivation`), tripping
  exactly as designed. The file was then restored from its
  pre-mutation copy and verified SHA-256-identical to the
  shipped hash (`f9c8ea10…`); the suite re-ran green. Recorded
  in `tests/README.md`; the raw failure list is in
  `scratch/additions_mutation_run.txt`.
