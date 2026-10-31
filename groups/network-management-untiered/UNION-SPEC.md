# Union Spec — Network Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set**: **2 forks**, category
**Network Management**, **tier null**. Every member's FedRAMP
impact level is **Unknown** in the source dataset — the source
publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The
Documented control claims section below replaces the baseline
section a tiered group's union spec carries.

Membership is exactly census unit `untiered:Network Management`
in `../../remainder.json` (2 fork IDs, verified mechanically).
Neither fork is filed under Network Management in `forks.json` —
Armada is filed **Fleet Management** and IronWiFi is filed
**Cybersecurity & Risk Management** — and both carry Network
Management among their source `business_categories`; the census
assigned both to this category from their own descriptions, and
the spec sheets record the assignment. Authorization status as
recorded is Initial Implementation for both — a status is record
data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined
by FedRAMP ID. Both descriptions were present in the cached
dataset and match `../../remainder/uncovered.json` — Armada's
exactly, IronWiFi's after the founding whitespace normalization
(its paragraph breaks collapse to single spaces; the only
difference in the set, pinned by test).

**What these forks actually are, stated plainly:** Armada is a
cloud SaaS console for provisioning and remotely managing
satellite communications terminals and connected assets, with
fleet mapping, statistics and reporting, configurable alerting,
incident lifecycle management, and audit logging. IronWiFi is a
vendor-neutral network authentication layer — cloud RADIUS,
802.1X/EAP-TLS, a cloud PKI, captive portals, and Wi-Fi identity
threat detection — that works with the customer's existing
network hardware and the identities the customer already manages.
Neither description is written in the founding fork's
vocabulary, and the taxonomy below was not re-tuned for them.

## How functions were counted

The category's fixed 12-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../network-management-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 12 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim table
exactly — 1 of 1 forks, 12 of 12 claims, deep-equal** against
the sheet at the founding ship commit (`4b65a0e`) — using the
founding normalization (zero-width characters removed, all
whitespace collapsed to single spaces — the founding rule for
this category, which subsumes the carriage-return-to-space
normalization other categories document), the founding sentence
split ("U.S." protected), and the founding evidence rule (first
sentence containing any of a family's verbatim patterns as a
case-sensitive substring).

The founding group's recorded wording-artifact corrections are
embodied in the taxonomy patterns and its adjudication log
(sentences that are marketing prose tag nothing; "(AI)" is a
gloss on network intelligence, not a second claim; "FIPS" is a
fork's platform property, never the build's; "manage" is a
verbatim substring and also fires inside "management" and
"managed", recorded rather than hidden; no reporting family and
no audit family exists in this taxonomy). An exclusion pass
scanned every raw hit's evidence sentence for third-party
catalogue segments and scope-exclusion phrasing: **no hits were
removed** — neither description contains a third-party catalogue
segment in its matched text (IronWiFi's `certified_services`
record field, which names role-based access and reports, was
never matched: the house method matches `service_desc` only),
and no evidence sentence carries scope-exclusion phrasing.
Adjudications and wording artifacts are itemized in
`scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not
a ceiling. **2 claims** across the set; **both forks carry one
claim** — there is no zero-claim fork, and the thinness of the
result (one family of twelve claimed) is the finding, recorded
not repaired.

Census citations: 2 citations are recorded for these forks in
the census; **2 of 2 verify** as verbatim substrings of the
forks' own descriptions (whitespace-normalized), and **1 of 2**
is itself a claim evidence sentence (Armada's opening sentence).
IronWiFi's citation — its works-with-any-access-point sentence —
tags nothing. Verification is not a claim, in either direction;
the per-citation record is `scratch/citation_check.json`.

## Function ranking — all 12 families

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Network management | 2 | **Core** — network registry, device inventory, and configuration change records |
| 2 | Cloud-managed networking platform | 0 | **Core substrate** (the registries and API cloud management runs on) — **zero claimants in this set; named absence** |
| 3 | Network deployment | 0 | **Core slice** (deployment as registration records; the provisioning engine is Extended) — **zero claimants in this set; named absence** |
| 4 | Network optimization | 0 | Extended (optimization engine) — **zero claimants in this set; named absence** |
| 5 | Network intelligence (AI) | 0 | Extended (intelligence / inference engine) — **zero claimants in this set; named absence** |
| 6 | Open APIs | 0 | **Core** (the build is API-first) — **zero claimants in this set; named absence with substance** |
| 7 | Process integration & automation | 0 | **Core slice** (automation definitions registered as data, never executed) — **zero claimants in this set; named absence** |
| 8 | Customizable monitoring & management | 0 | **Core** (telemetry records and alert records) — **zero claimants in this set; named absence with substance** |
| 9 | Platform scalability | 0 | Platform note (deployment layer) — **zero claimants in this set; named absence** |
| 10 | Telemetry data protection | 0 | **Core** (telemetry records held in the registry; FIPS-validated cryptography is a named gap, SC-13) — **zero claimants in this set; named absence** |
| 11 | U.S. data residency | 0 | Platform note (deployment property) — **zero claimants in this set; named absence with substance** |
| 12 | Network device offering (switching, wireless, security & SD-WAN) | 0 | **Core** (device inventory records by class; the hardware itself is not software) — **zero claimants in this set; named absence** |

The one claimed family, at its two weights: Armada's
`network_management` stands at **full weight** — its evidence
sentence states the offering's own remote management of
satellite terminals through a unified management console.
IronWiFi's stands at **artifact weight** — the verbatim pattern
`manage` fires on "the identities you already manage", identities
the *customer* manages in its own IdP; the offering is an
authentication layer, and the claim is recorded at artifact
weight in `scratch/ARTIFACTS.md`, not read as evidence that
IronWiFi performs network management.

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's twelve-function substrate **whole** — customer
organizations & membership; network registry; device inventory;
configuration change records; automation definition registry
(definitions are data, **never executed**); telemetry records;
derived device status; alert records; registry search & summary;
API access; access control; audit log. The substrate is records
machinery, and it is tier-independent code: the founding source
contains no tier or baseline machinery beyond a docstring naming
the founding build, so there was nothing tier-shaped to strip.
In this set, claim support is stated per function, honestly:
**network management** (Core functions 2, 3, and 4 — the network
registry, device inventory, and change records are the records
surface of managing networks) is claim-supported by both forks
under the standing disposition, Armada at full weight and
IronWiFi at artifact weight only. The **audit log** (Core 12) is
supported at the documented-prose tier by Armada's "audit
logging" capability and IronWiFi's per-authentication logging
sentence (see Documented control claims) — this taxonomy has no
audit family, so the support is prose weight, stated as such.
Every other core function is **carried, not claimed** in this
set: organizations & membership are the scoping container the
house pattern requires; the automation registry, telemetry
records, derived status, alert records, search & summary, API
access, and access control are substrate the claimed management
function presupposes, and two of them (alert records, API
access) have substance in these descriptions in other words —
recorded under Named absences, not converted into claims.
Functions are **carried** as substrate; no function is claimed
to be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/netmgmt/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `netmgmt` under `src/`, ids sequential
per object type with fixed prefixes (`org-`, `net-`, `dev-`,
`tel-`, `chg-`, `aut-`, `alr-`), failed operations consume no
id and change nothing, all timestamps UTC ISO-8601, roles
`admin|member|viewer` with the founding permission matrix
layered with organization membership, and the audit log
append-only with denied attempts recorded.

Three category invariants are preserved exactly, as the founding
build implements them: a device's freshness status
(`fresh` / `stale` / `unknown`) is **derived at read** from its
latest telemetry record against a stated 24-hour window and is
**never stored** — the stored device record carries exactly its
nine pinned keys and no derived key; change records never touch
devices (closing an approved change records intent and modifies
no device or network record, and the decider of a change is
never its requester); and no entity shape has a field for an IP
address, MAC address, serial number, credential, or any
identifier of a live network — references are opaque and
caller-chosen, and telemetry values are integers only, rejected
at the boundary otherwise. The summary computes counts only —
no score, rating, or health value exists on any view.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded here with its evidence; it is not the build's control
attainment, and nothing in this section fills a family in from
any baseline.

Control areas **documented** by at least one fork in the set:

- **Identification & authentication (IA)** — **IronWiFi**, whose
  description is authentication language throughout: "adds
  certificate-based authentication and policy", "Users and
  devices authenticate against Microsoft Entra ID (commercial
  and GCC High), Google Workspace, Okta, and LDAP or Active
  Directory", "Device certificates are issued and renewed by
  the built-in cloud PKI over SCEP". Authentication is this
  fork's documented core function; it is recorded here because
  this taxonomy carries no identity family — it is not
  converted into a taxonomy claim.
- **Access control (AC)** — documented **in part**: IronWiFi's
  "certificate-based authentication and policy" and its guest /
  sponsored-access prose (branded captive portals, vouchers,
  sponsored access) are access-policy language; Armada's
  "centralized connectivity provisioning … through a unified
  management console" is provisioning language at prose weight.
  Neither description states role-based access or least
  privilege in its own words (IronWiFi's `certified_services`
  record field does name role-based access — a record field,
  never matched, and not counted here).
- **Audit (AU)** — **Armada** ("incident lifecycle management,
  and audit logging", in its capability list) and **IronWiFi**
  ("Every authentication is logged per user and device"). Both
  stand at documented-prose weight: this taxonomy has no audit
  family, so neither is a taxonomy claim.
- **Cryptographic protection (SC)** — documented **in part**,
  at prose weight: IronWiFi names its mechanisms — EAP-TLS and
  a cloud PKI issuing and renewing device certificates over
  SCEP. No fork here claims FIPS-validated cryptography:
  IronWiFi's FIPS mention is a FIPS 199 *categorization*, and
  Armada's description contains no cryptographic language.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, CA, CM, CP,
IR, MA, MP, PE, PL, PM, PS, RA, SA, and SI **as control claims**
— is asserted by no description in the set. Two bounds are
stated explicitly: Armada's "incident lifecycle management" is
an operational function of its platform, not incident-response
control language about the offering, and is not documented as
IR; IronWiFi's ITDR flagging of credential misuse and anomalous
access is detection function prose, not an SI control claim.
IronWiFi's SOC 2 Type II sentence is a compliance assertion
recorded as the fork's own statement; it documents no family
here. IronWiFi's "FIPS 199 impact categorization Moderate" prose
— which in the same paragraph expressly disclaims a FedRAMP
Moderate Authorization — is recorded as the fork's statement
and, per the tier discipline above, moves no tier: the record
says Unknown, and Unknown is what the sheet records. If the
source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

Eleven of the twelve families stand at **0 of 2** (each is
listed in the ranking table above). The ones with substance in
other words, stated plainly:

- **Network deployment — 0 of 2, substance present.** Armada's
  prose is provisioning throughout ("centralized connectivity
  provisioning", "terminal and data-pool provisioning and
  management"); the family's pattern is "deploy", which occurs
  nowhere in either description.
- **Open APIs — 0 of 2, substance present.** IronWiFi "reports
  through the console, API and webhooks" and offers "a REST
  API"; the family's phrase "open APIs" never occurs.
- **Customizable monitoring & management — 0 of 2, substance
  present.** Armada offers "configurable alerting" and "network
  statistics"; IronWiFi is in part a "monitoring layer". The
  family's phrase occurs in neither.
- **U.S. data residency — 0 of 2, substance present.**
  IronWiFi is "delivered as SaaS on Google Cloud with US
  regions available"; the family's phrase is "stores data on
  U.S. soil".
- **Cloud-managed networking — 0 of 2.** Armada is
  "cloud-based" and IronWiFi is a "cloud RADIUS" / "cloud PKI";
  the founding fork's headline phrase "cloud-managed" is
  written by neither.
- **Network device offering — 0 of 2.** IronWiFi expressly
  works with the customer's existing access points, switches,
  and controllers "without replacing hardware"; Armada manages
  satellite communications terminals but never writes the
  family's phrase.
- **Network intelligence (AI) — 0 of 2.** Armada's Bridge
  sentence ("orchestration of GPU hardware to enable sovereign
  AI factories") is GPU orchestration, not network
  intelligence; IronWiFi's ITDR is threat detection. Neither is
  the family's phrase, and neither is recorded as an AI claim.
- **Reporting — no family exists.** As in the founding group,
  this taxonomy has no reporting family; Armada's "network
  statistics and usage reporting" is reporting substance with
  no family to claim it (the Core's registry summaries are
  substrate, not a reporting claim).
- **Audit — no family exists.** Armada's "audit logging" and
  IronWiFi's per-authentication logging stand at the
  documented-prose tier (AU, above), never as taxonomy claims.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented. The founding group's engine gaps (network
optimization engine; network intelligence / AI engine; device
provisioning & deployment engine; network configuration push /
control plane; firmware management engine; traffic control &
SD-WAN policy engine; telemetry collection & polling engine;
alert evaluation & delivery transport; integration connectors;
automation execution engine; cloud management web application;
FIPS-validated cryptography, SC-13) stand registered under the
founding group and are **not re-registered here**; two of them
gain substance from this set — the alert evaluation & delivery
gap (Armada's "configurable alerting") and the telemetry
collection gap (Armada's "network statistics") — noted, not
duplicated.

New from this set's forks:

- [ ] Network access authentication, RADIUS & 802.1X engine (IronWiFi's whole function; no taxonomy family exists for it)
- [ ] Cloud PKI & certificate lifecycle engine (issuance and renewal over SCEP)
- [ ] Wi-Fi identity threat detection (ITDR) engine
- [ ] Captive portal & guest / roaming access services (vouchers, sponsored access, OpenRoaming)
- [ ] Satellite communications terminal provisioning & connectivity management (Armada)
- [ ] Fleet mapping & geospatial awareness platform (Armada)
- [ ] Incident lifecycle management engine (Armada; the substrate's change records are not an incident lifecycle)
- [ ] GPU orchestration for sovereign AI factories (Armada Bridge — fork excess)
- [ ] Platform layer (encryption at rest; TLS when configured; multi-tenancy operation; demo identities not an IdP — IA-2 stays with the embedding organization)

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Network
Management`; 2 taxonomy claims tagged from the forks' own
descriptions (both forks claiming exactly one family,
`network_management` — Armada's at full weight, IronWiFi's at
artifact weight); the twelve-function substrate carried
byte-identical from the founding Network Management L2 build
and re-anchored to tier null; tier null recorded on every sheet
and pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
any fork or for the build itself.
