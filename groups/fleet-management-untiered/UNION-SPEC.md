# Union Spec — Fleet Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 15**: **2 forks**, category
**Fleet Management**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes
no baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's union
spec carries.

Membership is exactly census unit `untiered:Fleet Management` in
`../../remainder.json` (2 fork IDs, verified mechanically). Both
forks are filed **Fleet Management** in `forks.json`, and both
carry the same source business categories, [Fleet Management,
Operations Management]; the census assigned both to this category
from their own descriptions, and the spec sheets record the
assignment. Both forks' recorded authorization status is **Initial
Implementation** — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. Both descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (2/2).

**Duplicate pair:** FR2633153272 and FR2700857493 (Samsara Inc.,
Samsara Connected Operations Cloud, under two FedRAMP IDs) are
spec'd as separate sheets, per the Phase 1 rule that paired
records stay separate. Their descriptions are byte-identical in
the source (550 characters, three sentences) and their claim
tables are identical (2 claims each); the sheets differ only in
fork_id and source record. The pair is counted twice in every
count below, as the registry counts it. The census itself flags
the second record as "Duplicate listing of FR2633153272, same
description."

## How functions were counted

The category's fixed 17-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../fleet-management-l1/scratch/extract.py`, parsed, never
executed) and asserts it is the same 17 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 2 of 2 forks, 12 of 12 claims, deep-equal** against the
sheets as shipped — using the founding sentence split and evidence
rule (first matching sentence; over 400 characters, truncated to
397 + '...'), including the founding normalization (carriage
returns become spaces before sentence-splitting; neither
description in this set contains a carriage return, asserted in
the extractor, so the normalization changes nothing here).

The founding group's recorded wording-artifact discipline was
applied as recorded judgment, itemized for this set in
`scratch/ARTIFACTS.md`: the founding BROAD first-pass patterns,
run over this set's two descriptions as calibration only, produced
16 fork × family hits → **4 final claims** (**12 false hits
removed, 0 true hits recovered, 2 evidence re-bases** with count
unchanged — bare "fleet"/"vehicle" nouns tagged as a registry;
"driver workflows" and "customers" tagged as operator records;
"software-as-a-service" tagged as maintenance; "reporting" in a
list and "visibility" tagged as reporting/analytics; "driver" +
"compliance" tagged as ELD; "visibility" tagged as search; and the
API claim re-based from the bare "platform" noun to the open-APIs
sentence). An exclusion pass scanned every tightened raw hit's
evidence sentence for third-party catalogue segments and
scope-exclusion phrasing: **no hits were removed** — no evidence
sentence is a catalogue segment or carries scope-exclusion
phrasing. The forks' `certified_services` record fields (non-empty
for both) were **never matched**: the house method matches
`service_desc` only, and the claims below stand on the
descriptions' own sentences.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**4 claims** across the set; **both forks carry 2 claims; there is
no zero-claim fork**. The descriptions are short (550 characters,
three sentences each) and no conclusion about the real Samsara
product should be drawn from the tag count.

Census citations: 4 citations are recorded for these forks in the
census (2 per fork); **4 of 4 verify** as verbatim substrings of
the forks' own descriptions, and **2 of 4** are themselves a claim
evidence sentence (each fork's second sentence, the telematics
evidence). Verification is not a claim, in either direction: the
first citation (each fork's opening positioning sentence) tags
nothing, and the API claim stands on the third sentence, which the
census did not cite. The per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 2 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Live telematics & GPS tracking | 2 | Extended — "Live telematics & GPS streaming" (the founding group's named absence gains 2 claimants in this set; the streaming engine is not built and the substrate holds no telemetry stream) |
| 1 | API & integrations | 2 | The substrate's API access is **carried** (the build's REST contract, as in every group); external integration engines & connectors are Extended |
| 3 | Vehicle & asset registry | 0 | **Core** — Core 1 (carried; 0 claimants in this set) |
| 3 | Vehicle reservation & assignment | 0 | **Core** — Core 3 (carried) |
| 3 | Check-in / check-out activity records | 0 | **Core** — Core 4 (carried) |
| 3 | Usage & odometer records | 0 | **Core** — Core 5 (carried) |
| 3 | Operator / driver credential & account records | 0 | **Core** — Core 2 (carried) |
| 3 | Maintenance & inspection records | 0 | **Core** — Core 6 (carried, flagged — the founding posture for this record type) |
| 3 | EV charging stations & sessions | 0 | **Core slice** — Core 7 charging-session records (carried); live station communication & session control Extended |
| 3 | Payment processing | 0 | Extended — "Payment processing" |
| 3 | Demand & capacity forecasting | 0 | Extended — "Demand & capacity forecasting engine" |
| 3 | Reporting & analytics | 0 | **Core slice** — Core 8 reporting over registry records (carried, flagged; substance present in both descriptions, family phrase absent — see Named absences). Engines beyond that Extended |
| 3 | Access control & user validation | 0 | Core 10's RBAC hooks are the substrate answer (baseline-neutral at tier null, flagged); no fork here claims user validation |
| 3 | Dispatch routing & optimization | 0 | Extended — "Dispatch routing & optimization" (**zero claimants; named absence**) |
| 3 | ELD / hours-of-service integration | 0 | Extended — "ELD / hours-of-service integrations" (**zero claimants; named absence — the set's headline absence**) |
| 3 | Audit logging | 0 | **Core** — Core 10 (carried as baseline-neutral hooks, flagged) |
| 3 | Search | 0 | **Core** — Core 9 (carried; substrate operation over the build's own registry metadata, flagged) |

**The set's character, recorded honestly:** both records are the
same product — a connected-operations platform whose description
is three sentences about connecting vehicles, equipment, sites,
and workers: IoT devices (vehicle gateways, dash cameras,
environmental sensors) transmitting data to a cloud platform
offering fleet telematics, video-based safety, equipment
monitoring, driver-workflow, and regulatory-compliance
applications, with dashboards, alerting, reporting, and open APIs.
Almost everything the description *does* — video safety, equipment
monitoring, alerting, driver workflows — has **no family in this
category's taxonomy**, because the taxonomy was defined from the
founding group's two thin descriptions (an FMIS and an
EV-charging transaction system). That mismatch is recorded, not
repaired: the taxonomy was not re-tuned, and the unmatched
substance is named under Gaps, not forced into families.

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — vehicle & asset
registry; operator records (opaque references only); reservation &
assignment records with lifecycle; check-in / check-out activity
records; usage & odometer records (monotonic rule); maintenance &
inspection records (due status derived at read, never stored);
charging-session records; reporting over registry records; search
over registry metadata; RBAC + append-only audit log. The
substrate is records machinery that fleet operations presuppose,
and it is tier-independent code: the founding source contains no
tier or baseline machinery, so there was nothing tier-shaped to
strip. Where the founding contract's text says "Low baseline
hooks" for RBAC and audit, read it here as **baseline-neutral
hooks**: at tier null they are substrate, claimed against no
baseline.

Claim support in **this** set, stated per function honestly:
**none of the ten numbered Core functions is claim-supported by a
family in this set** — every Core family's count here is 0 of 2,
exactly as the founding group itself flagged its carried items
(maintenance records, search, RBAC + audit were 0/2 there too).
The set's two claimed families land outside the numbered Core:
`telematics_gps` (2/2) is an Extended engine, and
`api_integrations` (2/2) supports the substrate's API surface —
both forks claim "open APIs for integration with customer
systems," and the build's REST API is its implementation contract,
carried in every group; in the founding group that family was 0/2
and absent from the union entirely, so the support here is
recorded as a difference, not back-read into the founding spec.
Functions are **carried** as substrate; no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/fleet/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `fleet` under `src/`, ids sequential per object type with
fixed prefixes (`veh-`, `opr-`, `res-`, `chk-`, `use-`, `mnt-`,
`chg-`), failed operations consume no id and change nothing, all
timestamps UTC ISO-8601, roles `admin|manager|viewer` with the
founding permission matrix, maintenance due status derived at read
time via `_derive_due_status` and never stored (the stored record
carries no status field), operator records holding opaque
caller-supplied references only (no real PII fields), and the
audit log append-only with denied attempts recorded.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**; it is not the
build's control attainment, and nothing in this section fills a
family in from any baseline.

Control areas **documented** by at least one fork in this set:
**none.**

The one control-adjacent phrase in either description —
"regulatory compliance" (sentence 2, both forks) — names an
*application area* the platform offers ("applications for fleet
telematics, video-based safety, equipment monitoring, driver
workflows, and regulatory compliance"); it asserts no control
family about the offering itself and is recorded here as prose,
not as a documented control claim. No description in this set
contains access-control, authentication, authorization, audit,
encryption, or assessment language in any form (pinned by test).

Control areas **not documented** by any fork in this set: every
NIST SP 800-53 control family — including AC, AT, AU, CA, CM, CP,
IA, IR, MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control
claims** — is asserted by no description in the set. If the source
later publishes an impact level for any of these offerings, the
tier is recorded then and not before.

## Named absences

- **ELD / hours-of-service integration — 0 of 2 (headline).** The
  descriptions carry "driver workflows, and regulatory compliance"
  — a driver-workflow application area and a compliance
  application area, not an electronic logging device or an
  hours-of-service function (founding ARTIFACTS item 6 class). The
  vendor's ELD business elsewhere is reputation, not evidence; the
  absence stands, as it did for this category's L2 singleton
  (Geotab), whose ELD absence survived despite that vendor's ELD
  business.
- **Reporting & analytics — 0 of 2, substance present.** Both
  descriptions list "dashboards, alerting, reporting" and promise
  "real-time operational visibility," but the family's phrase
  "reporting and analytics" occurs nowhere (the word "analytics"
  occurs nowhere at all). The removal is recorded in
  `scratch/ARTIFACTS.md` item 4, not repaired; Core 8 is carried,
  flagged.
- **Maintenance & inspection records — 0 of 2.** "Equipment
  monitoring" is present and is not maintenance; no description
  contains maintenance or inspection vocabulary — the same result
  as the founding group (0/2 there too).
- **Vehicle & asset registry — 0 of 2.** No FMIS phrase; connecting
  vehicles is not a registry claim (founding item 2 class).
- **Access control & audit logging — 0 of 2 each.** No
  authorized-user, validation, role, or audit wording occurs
  anywhere in either description.
- **All remaining families — 0 of 2:** vehicle reservation,
  check-in/check-out, usage & odometer records, operator records,
  EV charging, payment processing, demand forecasting, dispatch
  routing, and search are claimed by neither fork; several (usage,
  operator records) are broad-vocabulary near-misses recorded in
  `scratch/ARTIFACTS.md`, and the rest have no vocabulary in the
  descriptions at all, even under the broad patterns.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
restated here where this set's forks claim or describe them
(claimant counts are this set's):

- [ ] Live telematics & GPS streaming (2 claimants — the founding group's named absence gains claimants in this set; the telemetry firehose and live vehicle tracking behind the claim are not built)
- [ ] Integration engines & external connectors (2 claimants — the "integration with customer systems" behind the open-APIs claim; the build's own REST API is its contract, not a connector engine)
- [ ] Video-based safety & dash-camera analytics engines (substance in both descriptions — "video-based safety", dash cameras — with no family in this taxonomy)
- [ ] IoT device telemetry ingestion & equipment / environmental monitoring engines (substance in both descriptions — vehicle gateways, environmental sensors, equipment monitoring — with no family)
- [ ] Alerting & notification engines (substance in both descriptions — "alerting" in the platform's feature list — with no family)
- [ ] Driver workflow & compliance applications (substance in both descriptions — "driver workflows, and regulatory compliance" — with no family; the ELD / hours-of-service integration gap itself stands registered from the founding group, at 0 claimants here)
- [ ] Dashboarding front-ends beyond registry reporting (substance in both descriptions — "dashboards" — with no family; engines beyond registry reporting stand registered from the founding group)
- [ ] Platform layer (encryption at rest, TLS-when-configured, multi-tenancy — the build performs no cryptography of its own and is a single-tenant reference deployment; demo identities are hooks, not an IdP)

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Fleet Management`;
4 taxonomy claims tagged from the forks' own descriptions (2 of 2
forks claiming, no zero-claim fork); the ten-function substrate
carried byte-identical from the founding Fleet Management L1 build
and re-anchored to tier null; tier null recorded on every sheet
and pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for any
fork or for the build itself.
