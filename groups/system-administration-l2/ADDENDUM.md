# Addendum — System Administration, CMMC L2 (DeadRamp Phase 2 remainder, unit `addition:system-administration-l2`)

The union spec for the enlarged group. The shipped UNION-SPEC.md
stands as written for the original fork; this addendum records
what joined, what the newcomers claim under the group's taxonomy,
what changed in the union (and what deliberately did not), and
the new gaps. Read together: UNION-SPEC.md + this addendum = the
spec of record for all 9 forks.

## 1. What joined

8 previously uncategorized forks, assigned to System
Administration by the remainder census (`REMAINDER.md` /
`remainder.json`, build unit `addition:system-administration-l2`)
from their own marketplace descriptions, each with the evidencing
sentences stored as census citations. All 8 are **FedRAMP
Moderate**, so they join at this group's tier by construction and
the baseline does not change: the union baseline remains the
tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, with the standing
caveat from `crosswalk.md` (this mapping is planning/matching
only; the build is not a FedRAMP authorization and confers no
CMMC certification).

| Fork ID | Vendor / Product |
|---|---|
| FR1819254092 | Citrix / Citrix for Government |
| FR1833967442 | Contegix / Valiantys Federal (Formerly Contegix) |
| FR2000951694 | DLH Corporation / DLH Infinibyte Cloud |
| FR2016131254 | Dynatrace / Dynatrace Platform |
| F1311252651 | ESRI / Esri Managed Cloud Services Advanced Plus |
| FR2215946050 | OpenText / ITMX Platform featuring Service & Asset Management, Universal Discovery, CMDB and Project & Portfolio Management |
| F1209041518 | Oracle / Federal Managed Cloud Services |
| FR2624215150 | TeamViewer / TeamViewer DEX Platform |

Their sheets are appended to `specs/specs.json` (entries 2–9).
The shipped sheet is preserved byte-for-byte: the append is a
pure insertion (asserted programmatically at build time by
`scratch/finalize_additions.py` — re-serialization of the shipped
sheet reproduces the shipped file exactly, and the new file's
text up to the shipped sheet's closing brace is identical to
it). One schema note: the shipped sheet took `deadramp_category`
from `forks.json`, which lists these 8 as "Uncategorized (none
in source)"; their appended sheets record the census-assigned
category, "System Administration", which is the category they
join. TeamViewer's authorization status is "Agency Authorization
In Process" (the other seven are FedRAMP Certified); recorded
as-is — status does not change tier or membership.

## 2. How the additions were spec'd

The group's **existing 8-family taxonomy was applied verbatim**
(`scratch/extract_additions.py` imports the taxonomy from the
shipped `scratch/extract.py`, so ids, labels, and patterns are
identical by construction). It was not re-tuned for the
newcomers. Census citations and taxonomy claims are different
instruments: a fork joins the group on its census citation (all
**13 citations verified** as verbatim substrings of the cached
descriptions), and it claims only the families the taxonomy
holds, with the first matching sentence stored as evidence
(every stored evidence sentence likewise verified as a verbatim
substring).

The taxonomy's patterns are the singleton's own exact phrases
("full management of the OS and services", "Highly Available
(HA)", "inherits controls from the CSP"), matched
case-sensitively, so the mechanical pass produced exactly **1
raw claim**, and it stands unchanged under the shipped group's
scoping discipline (a claim stands only when the matched text
asserts a customer-facing function of the offering). Final
result: **1 claim over 1 fork; 7 forks claim zero families.**
The zero-claim forks are not defective sheets: most newcomers
assert substantial managed-services substance one phrase away
from the patterns — "Operating System management and patching"
(Contegix), "application management" (Oracle), "application
deployment" (Esri), "highly available" without the parenthetical
(DLH). Those near-misses are itemized per fork in
`scratch/ADDITIONS_ARTIFACTS.md`, not rounded up.

Per-fork claims:

| Fork | Claims |
|---|---|
| Citrix for Government | virtualization_enablement |
| The other 7 additions | — (zero families) |

## 3. Claim ranking — enlarged group (9 forks)

| # | Forks (was) | Function family | Disposition (unchanged) |
|---|---:|---|---|
| 1 | 2 (1) | CSP virtualization of computing environments | Extended — the virtualization engine is the provider's |
| 2 | 1 | General Support System (GSS) of operating systems & services | **Core substrate** — the registries are the GSS's records surface |
| 2 | 1 | Full management of operating systems & services | Core slice — request/change records; the administration operations themselves Extended |
| 2 | 1 | Application delivery on the managed platform | Core slice — application registration records; delivery/hosting runtime Extended |
| 2 | 1 | Operation on third-party CSP hosting platforms | Platform note — systems record only an opaque `platform_ref` |
| 2 | 1 | Control inheritance from the underlying CSP | **Core** — control records carrying recorded sources verbatim |
| 2 | 1 | Highly Available (HA) network, up-time & redundancy | Extended — HA network operation is a platform operation |
| 2 | 1 | Access restricted to contracting organizations | **Core** — organizations with membership as the access boundary |

Group totals: **9 claims** (was 8). Only one family moved:
`virtualization_enablement` (1 → 2 forks).

## 4. Core-delta decisions

**Core delta: zero functions. `src/` is unchanged** — no core
extension was warranted, and none was made. Per claimed function:

- `virtualization_enablement` (1 new fork, Citrix) → **Extended,
  as before.** The family's disposition in the shipped union is
  Extended: the virtualization engine is the CSP's. Citrix's
  claim is a virtualization *product* (DaaS), which strengthens
  the gap, not the Core: the records the claim presupposes —
  customer organizations, the virtualized estate registered as
  managed systems known only by opaque references on an opaque
  `platform_ref`, delivered workspaces/applications registered as
  application records on those systems — are already Core 1–3,
  and a test exercises exactly that shape for the claimant. No
  new records function is presupposed that the substrate does
  not already hold, so the registry is not extended. A test pins
  that the store exposes no virtualization, hypervisor, or
  VM-provisioning entry point.
- All other families: no new claims → no delta, by construction.

Evidence that the code is untouched: `src/sysadmin/store.py`
SHA-256 `46c4f2dcc182d4ae288b5430c54f05478a81f937eb761d4f63270e7ed2a26719`
is identical to the shipped build's recorded hash
(`scratch/store.py.sha256`), and the additions mutation drill
(§6) was run against that exact file and restored to it.

## 5. Gaps — new and enlarged (for the GAPS.md final batch)

**New** — engines the additions bring that the shipped union's
gap list does not name:

- **Virtual workspace & desktop delivery platform** — workspace
  creation, management, and deployment; brokering and session
  delivery of virtual applications and desktops to end users
  (Citrix DaaS / Citrix Cloud).
- **Observability & AIOps platform** — metrics, traces, and log
  collection and analysis; continuous runtime application
  security analytics; AI-driven answers and automation from
  operational data (Dynatrace).
- **IT service & asset management suite (ITSM / ITAM)** —
  service-desk workflows, incident/problem processes, asset
  lifecycle governance, procurement, financial, vendor, and
  contract management processes (OpenText ITMX; Oracle FMCS's
  service desk and incident management ride the operations side
  of this gap).
- **Universal discovery & CMDB engine** — automated discovery
  and mapping of hybrid IT configurations, configuration-item
  records as a living CMDB, service dependency mapping and
  impact analysis (OpenText).
- **Project & portfolio management (PPM) platform** — strategic
  portfolio management, investment optimization, scenario
  planning (OpenText).
- **Digital employee experience (DEX) analytics & endpoint
  automation platform** — endpoint telemetry and experience
  analytics (including the vendor's own experience scores — an
  engine output, never computed here), remote endpoint
  investigation and remediation, endpoint automation and
  baseline enforcement, content distribution (TeamViewer DEX).
- **Geospatial (GIS) application platform** — the ArcGIS runtime
  and geospatial content services that Esri's managed service
  hosts (the payload, as distinct from the hosting operations).
- **Managed backup & disaster-recovery services** — managed
  backups, archive, disaster recovery and DR-as-a-Service
  operations (Contegix; DLH; Oracle FMCS; Esri EMCS).
- **Security operations services** — 24/7 security operations
  center, SIEM operation, vulnerability scanning services
  (Esri EMCS; Contegix; DLH scanning).

**Enlarged** — already registered under Group 54; the additions
change their weight, not their nature:

- **Managed OS & services administration operations** — was
  AMPS (1 of 1); the operating substance of Contegix, DLH,
  Oracle FMCS, and Esri EMCS joins it: **5 of 9** forks in the
  enlarged group are managed-services offerings whose work is
  this gap.
- **Virtualization engine** — was AMPS (an enablement aside,
  1 of 1); now asserted by **2 of 9** forks, and for Citrix it
  is the headline product function rather than an aside.
- **Application delivery & hosting runtime** — the managed
  hosting platforms (Contegix SecureCloud, DLH Infinibyte,
  Oracle FMCS, Esri EMCS) all deliver and host customer
  applications on their environments.
- **High-availability network operation** — count unchanged, but
  DLH asserts "highly available" platform substance (in
  lowercase, without a taxonomy claim) behind this gap.

**Named-absence updates.** The shipped singleton recorded
monitoring, incident response, ticketing/help-desk, SLA, and
backup/disaster-recovery vocabulary as absent from the category
record. Four of the five are **no longer universal absences** of
the enlarged group — monitoring (Contegix, DLH, Esri, Dynatrace),
incident response/management (Contegix, Oracle), ticketing and
service desk (Oracle, OpenText), and backup/disaster recovery
(Contegix, DLH, Esri, Oracle) are all asserted by addition
forks. They remain at **0 taxonomy claims and unbuilt**: the
taxonomy holds no family for them, none was added, and the
engines are gap-named above. **SLA / service-level vocabulary
remains a universal absence** — none of the 9 descriptions
states service levels, and request due dates remain the
substrate's records discipline, not an SLA claim.

Platform layer (unchanged, gap-listed as before): multi-tenancy
(Contegix and DLH assert multi-tenant delivery of their own
platforms; the build remains a single-tenant reference
deployment); encryption at rest (deployment layer); TLS only
when configured; demo identities are hooks, not an IdP — IA-2
stays with the embedding organization; part of each fork's own
baseline is satisfied by its underlying hosting platform
(control inheritance, recorded in Core as dispositions).

## 6. Verification (additions)

- Forks spec'd: **8 / 8**, each with its census citations
  verified verbatim (13 total); shipped sheet byte-preserved
  (append is a pure insertion; deep-equality against git HEAD
  verified).
- Core implemented: **12 / 12** (the shipped union core;
  extended by 0 functions — §4).
- Tests: **71 → 78** (new file `tests/test_additions.py`, 7
  tests: spec integrity, exact membership, house schema,
  taxonomy/verbatim-evidence audit, the exact claim map, the
  virtualization Extended honesty pin, and the claimant's
  records-substrate case). Full suite green.
- Negative control: the core is unchanged, so the group's
  signature drill was **re-run in this tree** (2026-10-31):
  `SysadminStore._is_overdue` patched to `return False` in the
  real `src/sysadmin/store.py` → **78 ran, exactly 6 failed**,
  the identical failure set to the shipped drill (2
  negative-control canonicals, 1 reporting summary, 2 requests,
  1 service full-flow); store restored and SHA-256-verified
  identical to the shipped hash; suite re-run **78, OK**.
  Record in `tests/README.md`; raw output
  `scratch/additions_mutation_run.txt`; pre-mutation copy
  `scratch/store.py.premutation.additions`.

## 7. Updated union statement

The enlarged group is **9 forks over one records substrate**.
The singleton was a government agency's own General Support
System; the additions make the group what the census found the
category actually is in the marketplace — predominantly
commercial managed-hosting and IT-operations offerings
(Contegix, DLH, Oracle, Esri), plus operations *platforms*
(Citrix, Dynatrace, OpenText, TeamViewer). Seven of the eight
newcomers claim nothing the taxonomy holds at all: they are in
this group because their own descriptions describe managed
platform services and IT operations (the census's
classification), not because their vocabulary matches one USDA
offering's. What their functions collectively presuppose is the
same substrate the singleton built — customer organizations,
managed systems, hosted applications, service requests,
changes, and control dispositions, under membership access
control and audit — and that substrate is what this build
implements once, at Moderate/L2. Above it the engines diverge
completely: virtual desktops, observability pipelines, GIS
hosting, service-management suites, endpoint experience
analytics. Every engine is named in §5. Nothing about the tier,
the baseline, or the 12-function core changed to admit them;
the one claim that joined landed in a gap the singleton had
already registered.
