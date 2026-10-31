# Addendum — Customer Service, CMMC L3-adjacent: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:customer-service-l3`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 10-function
core, its core-boundary decision, and its High control baseline are
**unchanged**. This document records what joined, what the newcomer
claims under the group's existing taxonomy, the core-delta decision,
and the updated union statement.

**Headline: fork spec'd 1 / 1; 2 new claims — the group total moves
0 → 2, and this tier gets its first claims; core delta — zero
functions extended, `src/` byte-identical; tests 112 → 126, all
passing; both signature drills re-run in this tree.** The newcomer
retires the category's standing named absence for satisfaction /
CSAT surveys at this tier and gives the already-registered AI
assistance gap a claimant here. **2 new gap functions** are named
in §5, and 1 already-registered gap gains a claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1711262842` | Medallia, Inc. / Medallia GovCloud |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact 16 (id, label, regex)
  triples** — the taxonomy was applied verbatim, not re-tuned for
  the newcomer. Same sentence splitting, same evidence rule (first
  matching sentence per family, stored verbatim), same sheet
  schema (the group's original 12 keys). Before tagging the
  newcomer, the extractor **reproduces the original fork's shipped
  claim table exactly from the raw cache** under the original
  scoping (see the exclusion note below) and asserts equality
  against the shipped sheet and against
  `scratch/function_counts.json`. The sheet is **appended** to
  `specs/specs.json` after the original, which is deep-equal to
  git HEAD and byte-preserved through its closing brace (asserted
  in the extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **High / Certified** (SaaS, Government Community Cloud), so the
  group stays single-tier and the High baseline is inherited in
  full (Merge Rules 1–2), unchanged. In the source the fork was
  **uncategorized** (`business_categories` empty; `forks.json`
  category "Uncategorized (none in source)"); the census proposed
  Customer Service, recorded on the sheet as the DeadRamp
  category.
- The census starting point was verified, not trusted: the fork's
  **2 census citations** were re-checked against its own cached
  description and **both verify** as verbatim substrings — with
  the twist recorded in §2: one citation tags no family, and the
  other is a claim's evidence sentence itself.
- **The group's signature exclusion trap does not apply to the
  newcomer.** FedHIVE's sheet exists at zero claims partly
  because its description's trailing catalogue of ~20 third-party
  hosted applications was excluded before matching (matching the
  full text would have manufactured 6 family hits, every one from
  another vendor's blurb — the accounting is reproduced exactly
  by this extractor before anyone is tagged). Medallia's record
  carries **no** `certified_services` block (empty, asserted in
  the extractor), and its description contains no catalogue of
  hosted applications and no scope-exclusion segment: the
  Salesforce / ServiceNow mention sits inside the fork's own
  integration bullet, describing connectors Medallia itself
  leverages — its own function prose, not applications hosted in
  its environment. Nothing was excluded; matched text is the full
  text, and raw hits equal surviving claims (2 = 2), with zero
  wording-artifact corrections. Only `service_desc` was matched,
  per house method.

## 2. What the addition claims

**2 claims**, both substantive — neither is a wording artifact,
and no correction was applied or needed:

| Family | Evidence (verbatim, first matching sentence) |
|---|---|
| `satisfaction_surveys` — Satisfaction / CSAT surveys | "Medallia captures experience signals created on daily journeys in-person, traditional surveys, on calls, digital channels, over video and social media, and IoT interactions." |
| `ai_assistance` — AI assistance / deflection / learned models | "Once net new data is captured or by leveraging legacy data previously collected by customers, Medallia applies proprietary AI technology on data that is structured and unstructured (text and comments) to reveal personalized and predictive insights that can drive action towards positive business / organizational results and outcomes." |

The per-sentence map is `scratch/additions_sentence_map.json`
(5 sentences under the group's splitting rule; 2 tag a family).

**The census twist, stated plainly.** Of the fork's 2 census
citations, the first ("The Medallia Experience Cloud (MEC), leads
the market in the understanding and management of experience for
agencies, public sector employees, and citizens.") tags **no**
family — it is market framing. The second citation **is** the
`satisfaction_surveys` evidence sentence above. Verification is
not a claim in either direction: a verified citation can tag
nothing, and here one verified citation and one claim coincide
because the census happened to cite the operative sentence.

**The named absence retires.** The union spec records of this
category: satisfaction / CSAT surveys are a **named absence** —
"claimed by no fork at any tier of this category; not built."
That was true when written and is no longer true of the enlarged
group at this tier: Medallia claims the family in its own words
(surveys are its first-named capture channel). The retirement is
pinned in `tests/test_additions.py`, not smoothed over. The other
standing named absence, knowledge base / help articles, is
claimed by neither fork and **survives** (§5).

**What the claims do not do.** Neither claim extends the core.
Satisfaction surveys were a named absence — never a core function
— and AI assistance is an Extended family (learned models) in
this category's union. The singleton's core-boundary decision
therefore stands verbatim for the enlarged group: all 10 core
functions remain **carried, not claimed**, now for both forks.
What changes is only the claim ledger above the substrate: the
tier's "0 tagged claims" headline is superseded. FedHIVE still
claims zero (twice over — its own prose produces no raw hits, and
the catalogue that would have produced 6 was excluded); the
newcomer claims the feedback layer of the category: collecting
experience signals and running models over them. The records that
layer's outputs would write — a flagged signal as a case record,
a spike as an alert record, a recovery notice as a public status
update — are forms the carried substrate already holds, which is
what the substrate cases in `tests/test_additions.py` exercise.

### Near-misses, itemized

- **`case_ticket_management`** — the fork does this family's work
  in substance and in other words: "achieve in-the-moment service
  recovery", "help resolve issues quickly", end-to-end experience
  management. But the description contains no ticket token, no
  standalone "case", and no triage vocabulary (pinned by regex in
  the tests). The family's operative text is absent; stays 0.
- **`alert_prioritization` / `event_detection_response`** — "Taking
  Action in Real-Time with analysis and alerts that identify focus
  areas and help resolve issues quickly" is alerting in substance.
  The patterns require "event orchestration", "intelligent
  aggregation", "prioritize critical alerts", "automated
  detection", or "incident management / resolution"; none appears.
  Both stay 0.
- **`realtime_channels`** — a channel inventory in substance:
  signals are captured "on calls, digital channels, over video
  and social media", and journeys span "email, mobile, websites,
  chat, phone, video, and contact centers". None of the family's
  operative phrases appears ("live chat", "voice channel",
  "telephony", "chat channel", "phone support"). Stays 0.
- **`reporting_dashboards`** — "actionable insights", "analysis",
  "drive data-driven business decisions" are analytics in
  substance; the tokens "analytics", "dashboard", and "reports"
  never appear. Stays 0.
- **`compliance_frameworks`** — "a platform that is FEDRAMP High
  certified with the JAB as well as HIPAA compliant" is
  certification prose about the vendor's own posture — a platform
  property that does not transfer to the build — and the verbatim
  patterns (`NIST 800-53`, `Risk Management Framework (RMF)`,
  `Authority to Operate (ATO)`) are absent. The same wording-miss
  shape as FedHIVE's recorded near-miss in this family. Stays 0.
- **Whole-description absences** — no "status updates" / "status
  pages" (`status_communication`), no access-control, role-based,
  or permissions vocabulary (`access_control`), no "audit log" /
  "audit trail" (`audit_logging`), no exact GRC phrase
  (`governance_risk_compliance`), no on-call, mobilize, knowledge
  base, or help-article vocabulary. Fourteen of the sixteen
  families stay at 0 for this fork, each on token-level evidence
  pinned in the tests.

## 3. Core-delta decision

| Family / substance (addition) | Disposition | Core delta |
|---|---|---|
| `satisfaction_surveys` (claimed) | Extended — a feedback-collection engine; the family was a named absence, never Core | **Gap** (§5) — not an extension |
| `ai_assistance` (claimed) | Extended — learned models over feedback data; already a registered gap in this category's union | **Gap** (§5) — gains a claimant; not an extension |
| Case / alert / status records the described surface presupposes ("service recovery", real-time alerts; asserted in substance, no claim) | Core 1, 5, 7 — already in the carried substrate | **Carried** — no change |
| Platform connectors & integration API surface (asserted in substance; no family in this taxonomy) | Extended | **Gap** (§5) — not an extension |

**Result: the core is unchanged.** The newcomer claims two
functions and both are Extended in this category's union; the one
substrate its described surface presupposes (case, alert, and
status records) is the build as shipped. `src/` is byte-identical
to the shipped build (all seven `src/custsvc/` module hashes
identical before and after this addendum's work, both mutation
drills included — e.g. `store.py` SHA-256
`40c4d9c6ad5f4b3f12c4876cd9de5ccdfe829bfc5578343b9585a4bd7cc2b24a`,
`audit.py` SHA-256
`3d0965771e6a38c3ddc3da82686a2afa55de6b5f20101d961e5d10ee308f8157`;
the full `src/` tree diff against HEAD is empty). The tier
baseline does not change: same tier by construction.

## 4. Updated union statement

The group now covers **2 forks** (1 original singleton + 1
remainder addition), **2 claims** in total (0 + 2), with **1 of
2** forks carrying at least one claim. The merged build remains
the same customer-service records substrate at the High baseline —
cases with a guarded lifecycle, requesters keyed by opaque
references only, assignment, priority/due records with breach
derived at read, alert records, on-call rotations, the derived
public status view, the never-executing rule registry, registry
reporting and search, RBAC with the auditor role, and the
append-only hash-chained fail-closed audit log — now spec'd
against 2 marketplace offerings instead of 1. The tier's picture
is a study in the category's two poles: a hosting boundary filed
under Customer Service whose own prose claims nothing at all, and
an experience platform that claims exactly the layer FedHIVE's
prose never touches — collecting citizen and employee feedback
and running models over it. The substrate serves both without
changing a line, which is what the core-boundary decision
predicted: the category union is carried up whole, and claims are
recorded where the words actually are.

## 5. Gaps — for the registry at ship

**New gap functions** (2):

- **Survey & feedback-collection engine** (citizen/employee
  experience-signal capture across in-person, survey, call,
  digital, video, social-media, and IoT channels; feedback
  response management) — Medallia GovCloud, claimed in its own
  words ("traditional surveys" is its first-named capture
  channel). Registered now **with** a claim, and it retires the
  named absence below. The records a flagged signal would write —
  case and alert records — are Core; the collection engine itself
  is Extended.
- **Platform connectors & integration API surface** (connectors
  for third-party platforms — Salesforce and ServiceNow are the
  two the fork names — plus a REST API suite for integration at
  scale) — Medallia GovCloud, from its own closing bullet
  ("Integrating at scale by leveraging connectors for platforms
  such as Salesforce and ServiceNow and supported by a robust
  suite of Restful API"). This taxonomy has no integrations
  family, so the function is asserted in substance only; no claim
  fired.

**Existing gaps gaining claimants** (1):

- **AI assistance / deflection / learned models** gains a claimant
  at this tier: Medallia's proprietary AI over structured and
  unstructured feedback data, producing personalized and
  predictive insights (claimed; the engine remains Extended).

**Existing gaps explicitly gaining no claimant** — itemized,
because three were plausible:

- **Event detection, diagnosis & orchestration engines** gains
  **no** claimant: "analysis and alerts that identify focus
  areas" is alerting prose without the families' operative
  phrases (§2). Alert *records* are Core 5; no engine is claimed.
- **Real-time channels (live chat, voice / telephony)** gains
  **no** claimant: the fork inventories channels in substance but
  names none of the family's phrases (§2).
- **Reporting / analytics engines** gains **no** claimant:
  "insights" and "analysis" are not the family's tokens (§2).
  Registry reporting is Core 9; no engine is claimed.

**Named absences:**

- **Retired at this tier: satisfaction / CSAT surveys** — claimed
  by the newcomer in its own words; see the first new gap above.
  (The L1/L2 groups' sheets are separate builds and are not
  rewritten by this addendum; the retirement is recorded for this
  group's registry entry.)
- **Surviving: knowledge base / help articles** — claimed by
  neither fork at this tier and, per the union spec, by no fork
  at any tier of this category. The description contains no
  knowledge-base or help-article vocabulary (pinned in the
  tests).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal
  two-claim table with its pinned evidence sentences, the
  original sheet's standing zero-claim table, the group totals
  (2 claims; exactly 1 zero-claim fork — the original), registry
  fields as published, the verbatim description, the census
  citations (both verify; the tagging twist pinned), the
  no-exclusion pin (empty `certified_services`), the named-absence
  accounting, and the near-miss token pins — see
  `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file: a
  feedback-signal case (opaque requester ref, channel "survey",
  past due) assigned and read back breached, with a linked alert
  worked to resolved and a public status update posted; and an
  audit-chain case in which the flow's trail verifies clean and
  an in-place mutation is localized at exactly index 1.
- **Tests: 112 → 126, all passing.**
- **Negative controls:** the core is unchanged, so the group's
  **both** signature drills were re-run in this tree. Drill 1
  (breach derivation): `_is_breached`'s final return in
  `src/custsvc/store.py` patched to `return False` (target line
  occurs exactly once; count asserted, patch scoped) — the full
  suite ran: **126 tests, exactly 8 failures**: the shipped
  drill's 7 plus 1 from the new additions module
  (`test_medallia_feedback_case_breach_flow`), tripping exactly
  as designed. Drill 2 (audit hash chain): the comparison in
  `verify_chain()` patched to `if False:` (exactly one
  occurrence, asserted) — **126 tests, exactly 3 failures**: the
  shipped drill's 2 plus 1 from the additions module
  (`test_medallia_audit_chain_detects_tampering`). After each
  drill the file was restored from its pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; the raw failure
  lists are in `scratch/additions_mutation_run.txt` and
  `scratch/additions_mutation_audit_run.txt`.
