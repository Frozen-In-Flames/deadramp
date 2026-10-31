# Union Spec — System Administration, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 10**: **4 forks**, category
**System Administration**, **tier null**. Every member's FedRAMP
impact level is **Unknown** in the source dataset — the source
publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The
Documented control claims section below replaces the baseline
section a tiered group's union spec carries.

Membership is exactly census unit `untiered:System
Administration` in `../../remainder.json` (4 fork IDs, verified
mechanically). In `forks.json` the set is mixed as filed: 2
forks are filed "Uncategorized (none in source)" (Dynatrace,
NetApp), 1 under Operations Management (Freshworks), and 1 under
Cybersecurity & Risk Management (PDQ); the census assigned all
4 to System Administration from their own descriptions
(classifier notes in `remainder.json`: observability platforms
whose primary stated function is unified observability of
systems; an IT service-management / IT-operations offering; an
endpoint management, patching and deployment platform for
sysadmins), and the spec sheets record the assignment. The
managed-platform boundary the census recorded stands as
recorded: this set's Freshworks fork is service-operations
prose the census placed here, and nothing in this build re-draws
that boundary. Authorization statuses as recorded span Initial
Implementation (3) and FedRAMP In Process (1) — a status is
record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) —
4 entries, each with the offering's full public marketplace
description and its function claims tagged from that
description, every claim carrying the source sentence as
evidence, every sheet recording `fedramp_impact_level:
"Unknown"` and `cmmc_tier: null`. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product records joined by FedRAMP ID. All 4
descriptions were present in the cached dataset; the census
carries the same records' `service_desc` verbatim in
`../../remainder/uncovered.json`, and the sheets store the
founding group's normalized form of that text (see below).

## How functions were counted

The category's fixed 8-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../system-administration-l2/scratch/extract.py`, parsed,
never executed) and asserts it is the same 8 families before
tagging. This taxonomy is unlike most in the repo: the founding
group is a singleton new category, so its families are the
founding fork's own exact phrases ("full management of the OS
and services", "Highly Available (HA)", "inherits controls
from the CSP", "General Support System (GSS)"), matched
case-sensitively.

Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim table
exactly — 1 of 1 forks, 8 of 8 claims, deep-equal** against the
singleton sheet at the founding ship — using the founding
extractor's own method: descriptions whitespace-normalized
(runs of whitespace collapsed to single spaces, ends stripped —
the founding group's documented normalization, its
ARTIFACTS.md item 1), the founding sentence split (on
`(?<=[.!?])\s+`), and the founding evidence rule (first
matching sentence; for `restricted_access`, the contract
sentence when present). The proof also asserts the reproduced
description equals the shipped sheet's stored description
byte-for-byte.

Applied verbatim to this set, the mechanical pass produced
**0 raw hits**: no taxonomy pattern occurs in any sentence of
any of the four descriptions. The exclusion pass (every raw
hit's evidence sentence scanned for scope-exclusion phrasing
and third-party catalogue segments) therefore removed nothing —
**0 hits removed, because 0 hits fired**. A function is claimed
for a fork **only** when its own description contains matching
text; counts are a **floor**, not a ceiling. **0 claims**
across the set; **all 4 forks carry zero claims**. The zeros
are recorded under Named absences, not hidden, and the
near-misses are itemized in `scratch/ARTIFACTS.md`: the
taxonomy phrases its families as one offering's exact wording,
and these four offerings assert their system-administration
substance — observability, IT service management, endpoint
management — in other vocabulary. The taxonomy was not
re-tuned for them (the founding additions' posture: 1 claim
over 8 forks, 7 zero-claim, near-misses itemized rather than
rounded up).

Census citations: 8 citations are recorded for these forks in
the census (2 per fork); **8 of 8 verify** as verbatim
substrings of the forks' own descriptions (under the founding
normalization), and **0 of 8** serve as a claim evidence
sentence — there are no claims for them to evidence.
Verification is not a claim, in either direction; the
per-citation record is `scratch/citation_check.json`.

## Function ranking — all 4 set members

Dispositions are the category's standing disposition per
family, taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 4) | Disposition in this build |
|---|---|---:|---|
| 1 | General Support System (GSS) of operating systems & services | 0 | **Core substrate** (the registries are the GSS's records surface; runtime platforms are the platform layer) — **no claimant in this set; named absence** |
| 2 | Full management of operating systems & services | 0 | **Core slice** (management work as service request and change records; the administration operations themselves are Extended) — **no claimant in this set; named absence** |
| 3 | Application delivery on the managed platform | 0 | **Core slice** (application registration records; the delivery/hosting runtime is Extended) — **no claimant in this set; named absence** |
| 4 | Operation on third-party CSP hosting platforms | 0 | Platform note (hosting platforms are outside any fork's own boundary here; systems record only an opaque `platform_ref`) — **no claimant in this set; named absence** |
| 5 | Control inheritance from the underlying CSP | 0 | **Core** (control records carrying each control's recorded source per managed system) — **no claimant in this set; named absence** |
| 6 | CSP virtualization of computing environments | 0 | Extended (the virtualization engine is a platform's) — **no claimant in this set; named absence** |
| 7 | Highly Available (HA) network, up-time & redundancy | 0 | Extended (HA network operation, redundancy, failover) — **no claimant in this set; named absence** |
| 8 | Access restricted to contracting organizations | 0 | **Core** (customer organizations with membership as the access boundary) — **no claimant in this set; named absence** |

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries
the founding group's twelve-function substrate **whole** —
customer organizations & membership; managed system registry;
application registry; service request records; derived request
status; change records; control inheritance records; registry
search; registry summary; API access; access control; audit
log. The substrate is the records machinery the founding
fork's claimed functions presuppose — the registry of the
customer organizations, managed systems, applications, service
requests, changes, and control dispositions a managed service
acts on — and it is carried here exactly as the founding build
implements it. **In this set, no core function is
claim-supported by any fork**: the set's four descriptions fire
no taxonomy family, so every function is **carried, not
claimed**. That is stated plainly rather than softened: the
substrate's warrant in this set is the category's merged
build, not these forks' wording. The founding group's six
core-boundary decisions carry with the substrate, unchanged:
(1) the substrate is scoped by customer organizations with
membership as the access boundary, organizations known only by
an opaque `ref` and a label; (2) management is work — the
substrate holds its records (service requests, changes);
recording a request performs no work, and closing a change
alters no system or application record, both pinned by test;
(3) requests are records, not a ticketing claim; (4) a
request's `overdue` flag is derived at read from the stored
due date and lifecycle status and is **never stored**;
(5) control records carry dispositions verbatim (`inherited` /
`local` / `shared`) and **no posture, score, or health value
is derived from them**, enforced by a recursive key scan over
every view; (6) no entity shape has a field for a hostname, an
IP address, a credential, or any live-system identifier —
managed systems and applications are known only by opaque
caller-chosen references, and the hosting platform only by an
opaque `platform_ref`.

The carried code is **byte-identical** to the founding group's
`src/sysadmin/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `sysadmin` under `src/`, ids sequential
per object type with fixed prefixes (`org-`, `sys-`, `app-`,
`req-`, `chg-`, `ctl-`), failed operations consume no id and
change nothing, due dates are `YYYY-MM-DD` calendar dates,
roles `admin|member|viewer` with the founding permission
matrix layered under organization membership, and the audit
log append-only with denied attempts recorded. Where the
founding contract's text and the carried `__init__.py`
docstring say "L2" / "Moderate baseline", read it here as the
founding group's label on carried code: at tier null the hooks
are baseline-neutral substrate, claimed against no baseline.
The founding group's named seams are preserved: `_is_overdue`
(the overdue derivation) and `_check_decider_not_requester`
(the separation-of-duties seam on change decisions — the
decider is never the requester).

**This build administers nothing.** It holds the records a
system-administration service acts on; it patches nothing,
provisions nothing, monitors nothing, and performs no
management work. The operations themselves are gaps, named
below.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 4 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded here with its evidence; it is not the build's control
attainment, and nothing in this section fills a family in from
any baseline. (The taxonomy families above are function
families; this section reads the descriptions' control
language separately, exactly as the founding spec separated
its baseline traceability from its claims.)

Control areas **documented** by at least one fork in the set —
all four by a single fork, PDQ (FR2701457585), in a single
sentence: "PDQ is SOC 2 certified and includes security
features such as MFA, role-based access controls, encryption,
and audit logging to support compliance requirements."

- **Identification & authentication (IA)** — PDQ: multi-factor
  authentication ("MFA") among its platform's security
  features.
- **Access control (AC)** — PDQ: "role-based access controls"
  on its platform.
- **Cryptographic protection (SC)** — PDQ: "encryption" among
  its security features. (The build performs no cryptography
  of its own; this is the fork's claim about itself.)
- **Audit (AU)** — PDQ: "audit logging" among its security
  features.

The same sentence's "SOC 2 certified" is recorded as the
fork's own certification statement about itself; it is not a
control family and this build neither relies on it nor repeats
it as a claim of its own.

Recorded but **not** traced to a family: Freshworks'
"built-in security, compliance, and governance controls"
(sentence: "Reduce costs and increase efficiencies with
transparent pricing and built-in security, compliance, and
governance controls") asserts governance in general terms and
names no control; it is recorded here as general-terms prose,
not as a documented control claim for any family. Freshworks'
incident/problem/change/request *management* and Dynatrace's
"application security" are **function prose** — services those
offerings sell — not control claims about the offerings
themselves, and are not documented here as control claims.

Control areas **not documented** by any fork in this set:
every other NIST SP 800-53 control family — including AT, CA,
CM, CP, IR, MA, MP, PE, PL, PM, PS, RA, SA, and SI **as
control claims** — is asserted by no description in the set.
If the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **All eight taxonomy families — 0 of 4, each.** General
  Support System; full management of operating systems &
  services; application delivery; third-party CSP hosting
  platforms; control inheritance; virtualization; Highly
  Available (HA) network; restricted access. No description in
  this set contains any family's verbatim phrase.
- **Zero-claim forks: all four.** FR2700555848 (Dynatrace) —
  observability prose; its closest approach, "the monitoring
  estate", names a function the taxonomy deliberately holds no
  family for. FR2630354491 (Freshworks) — ITSM/ITOM/ITAM
  prose; "IT Operations Management" is not "full management of
  the OS and services", and its incident/request management is
  a working system, not the records substrate. FR2217348295
  (NetApp Cloud Insights) — observability and capacity prose;
  "capacity management" is no family's phrase. FR2701457585
  (PDQ) — endpoint-management prose; "Multitenant management"
  is not "third-party cloud hosting platforms", and patching,
  deployment, and monitoring have no family here. The zeros
  are recorded, not repaired; the taxonomy was not re-tuned.
- **The founding group's named absences are asserted in
  substance here and still claim nothing.** Monitoring —
  Dynatrace, NetApp, and PDQ all assert monitoring in so many
  words, and the taxonomy holds no monitoring family (the
  founding spec names monitoring a named absence, not an
  attributed function). Incident management — Freshworks
  asserts an end-to-end major-incident platform; no family.
  Ticketing / service desk — Freshworks' ITSM is one in
  substance; the founding spec names no ticketing function,
  and Core's request records are records, not a ticket system.
  Backup/disaster recovery and SLA vocabulary appear in no
  description in the set either.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented — the founding group's operations gaps, restated
for this set, plus the engines this set's forks assert in
substance (claimant counts are this set's; the taxonomy
claimants for every line are 0 of 4, because the taxonomy
holds no family for them):

- [ ] Managed OS & services administration operations (the full management itself: administering, configuring, patching, hardening, and tending operating systems and services — performed by operators' people and platforms, never by this substrate)
- [ ] System provisioning & deployment operations (standing up OS instances and services on a hosting platform; the substrate registers systems, it does not provision them)
- [ ] Application delivery & hosting runtime (the hosting environment applications are delivered on and run in)
- [ ] Virtualization engine (a platform's virtualization of computing environments)
- [ ] High-availability network operation (the HA network, redundancy, and failover)
- [ ] Third-party CSP hosting platforms (outside any fork's own boundary as described; the substrate records only an opaque platform reference)
- [ ] Observability & monitoring engines (Dynatrace, NetApp, PDQ in substance — telemetry collection, infrastructure/application observability, log analytics)
- [ ] AI root-cause & predictive analytics engines (Dynatrace's causal/predictive AI over telemetry)
- [ ] IT service management systems (Freshworks ITSM in substance — incident, problem, change, and request management as a working system, on-call/alerting and major-incident coordination; Core holds the records such a system presupposes, not the system)
- [ ] IT operations & asset discovery engines (Freshworks ITOM dependency mapping and signal correlation; ITAM agentless discovery and inventory)
- [ ] Endpoint management operations (PDQ in substance — patch management execution, software deployment, remote desktop/diagnostics, event-driven endpoint automation; patching rides Core's change records as records only)
- [ ] Vulnerability detection & remediation prioritization engines (PDQ in substance)
- [ ] Capacity management, optimization & chargeback/showback reporting engines (NetApp in substance)
- [ ] Platform layer (encryption at rest and TLS are deployment-layer; multi-tenancy; demo identities are hooks, not an IdP — IA-2 stays with the embedding organization)

## Coverage statement (for this build)

4 forks spec'd of 4 in census unit `untiered:System
Administration`; 0 taxonomy claims tagged from the forks' own
descriptions (0 of 4 forks claiming at least one — the
mechanical pass produced no raw hits under the founding
taxonomy applied verbatim, and nothing was manufactured to
change that); the twelve-function substrate carried
byte-identical from the founding System Administration L2
build and re-anchored to tier null; tier null recorded on
every sheet and pinned by tests. Nothing in this build claims
a FedRAMP authorization, a CMMC certification, or a control
baseline for any fork or for the build itself.
