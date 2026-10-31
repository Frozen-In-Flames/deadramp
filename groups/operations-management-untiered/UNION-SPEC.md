# Operations Management — Untiered Set Union Spec

This set is **untiered**. Its 20 forks carry FedRAMP impact level
**"Unknown"** in the GSA FedRAMP Marketplace dataset — the source
publishes no baseline (Low / Moderate / High / LI-SaaS) for them, and
their census tier is **null**. No baseline is asserted for this set
because the source publishes none: this spec therefore carries a
**Documented control claims** section in place of a baseline section,
and draws **no CMMC equivalence**. (The standing tiered caveat — that
FedRAMP authorizes products while CMMC certifies organizations, and
that any tier mapping is a planning equivalence, never a credential
claim — is replaced here by the plainer statement above: there is no
tier to map.) A fork's documented control language is that fork's
claim, never this build's attainment.

## Membership (20 forks)

Exactly the forks of census build unit `untiered:Operations
Management` in `remainder.json` (`build_units`), verified mechanically
by `tests/test_specs.py`:

| Fork ID | Vendor / Product | Filed category in source |
|---|---|---|
| FR2701457595 | AtomAI Solutions Inc. / AtomAI Platform | Operations Management |
| FR2631054482 | Concourse Tech Inc. / Concourse Platform | Operations Management |
| FR2701256060 | Fulcrum / Fulcrum | Artificial Intelligence (AI) |
| FR2630354487 | Globality Inc / Globality Platform | Operations Management |
| FR2628943629 | International Vending Management, Inc. / SmartHub | Operations Management |
| FR2630354492 | MaintainX / MaintainX for Government | Operations Management |
| FR2631054487 | Nastro Technologies, Inc. / BitRip | Uncategorized (none in source) |
| FR2634659083 | NavigatorCRE / NavigatorCRE | Uncategorized (none in source) |
| FR2631258127 | NEXGEN Asset Management / NEXGEN Asset Management | Operations Management |
| FR2628647241 | Partos Inc. / Partos for Government | Artificial Intelligence (AI) |
| FR2628650874 | Pincus Technologies Inc / Tarly Cowork | Artificial Intelligence (AI) |
| FR2632436493 | Rohirrim, Inc. / Unified Acquisition Platform | Artificial Intelligence (AI) |
| FR2428039108 | Siemens AG / DepotFinity | Uncategorized (none in source) |
| FR2634659087 | Signifi Solutions Inc. / SignifiVISION | Uncategorized (none in source) |
| FR2633841585 | Silkline, Inc. / Silkline | Data Management |
| FR2310051488 | Standard Technology Inc. / Contract Management Planning and Surveillance System (COMPASS) | Operations Management |
| FR2630447318 | Stoke Space Technologies, Inc. / Boltline | Operations Management |
| FR2701247935 | Tansi LLC / Tansi | Uncategorized (none in source) |
| FR2316433331 | USU Solutions Inc. / USU IT Asset Management | Artificial Intelligence (AI) |
| FR2628943630 | Xfinion Inc. / Continuously Aware Realtime Tracking Network (CARTN) | Operations Management |

Every fork is SaaS in the source; 17 carry authorization status
"Initial Implementation" and 3 "FedRAMP In Process" (COMPASS, Tansi,
USU). Zero overlap with the founding group's 22 sheets. The
`deadramp_category` recorded on every sheet is the census assignment,
**Operations Management**; the filed categories above are kept visible
because nine of the twenty were filed elsewhere (five under Artificial
Intelligence (AI), one under Data Management) or nowhere (five
Uncategorized) — the census classified them here from their own
descriptions, and that classification is the census's, recorded
as-is.

## How functions were counted

The Operations Management category's taxonomy was applied verbatim:
the 19-family TAXONOMY literal was AST-parsed out of
`groups/operations-management-l2/scratch/extract.py` (parsed, never
executed) and asserted equal in count before any tagging. The
extractor first **proved** the verbatim application by reproducing the
founding group's original 2 spec sheets (git commit `497e8a6`) from
the raw cache — 2 of 2 sheets, 20 of 20 claims, deep-equal — and
asserted the enlarged parent file's first two sheets still equal the
original ship tables. Evidence rule, the parent's exactly: the first
matching sentence under the parent's sentence splitting (carriage
returns and newlines become spaces before splitting), stripped, no
truncation. Every claim in `specs/specs.json` stores its source
sentence as `evidence`; descriptions are stored as the source has
them (verified equal to the census's `remainder/uncovered.json`
descriptions byte-for-byte, 20 of 20).

Corrections applied — the founding group's recorded scoping judgment
(full record in `scratch/ARTIFACTS.md`):

- **7 raw hits removed, all in recorded classes.** Six
  `authorization_services` hits were boundary/status prose, not
  authorization offered as a service: MaintainX (authorization
  boundary), Tarly Cowork (the agency's ATO process), Rohirrim
  (authorization boundary), DepotFinity (authorization boundary),
  COMPASS (its hosting platform Azure Government's P-ATO status),
  USU (ATO-support tasking for one named customer). One
  `workflow_automation` hit was a name-only token: COMPASS's
  "Automation" inside "Security Content Automation Protocol (SCAP)",
  an external standard's name in a third-party services list.
  The extractor removes a hit only when its evidence falls in the
  recorded class (markers asserted); an authorization hit outside
  the class would have survived for explicit review — none occurred.
- **Re-anchoring check:** every removed (fork, family) was checked
  for a second, function-asserting matching sentence in the same
  description: 0 in all 7 cases. No claim waits behind a removal.
- **Exclusion pass:** every raw hit's evidence sentence was scanned
  for scope-exclusion phrasing; no flags. COMPASS's long list of
  third-party services and tools it "utilizes and/or offers" (Tenable,
  AppScan, Sentinel, Rapid7, Fortify, and similar) was scanned in
  full; no pattern fires on it beyond the SCAP name token. Third-party
  catalogues stay excluded, and the scan is recorded so the silence
  is auditable.
- **Census citations are not claims.** 29 of 29 census citations
  verified as verbatim substrings of their descriptions; exactly 1
  (Boltline's `integrations` evidence sentence) serves as a claim
  evidence sentence. The other 28 verify as classification prose
  only — verification is not a claim, in either direction.

**Result: 2 claims across 20 forks. 18 forks are zero-claim.** The
founding group's no-zero-claims floor (every fork claimed something)
does not survive contact with this set, and nothing was manufactured
to preserve it: the taxonomy was not re-tuned, no substance was
promoted to a claim, and the near-miss record in
`scratch/ARTIFACTS.md` names what the phrases missed.

## Function ranking (this set's counts; dispositions are the category's standing ones)

| # | Function | Forks claiming (of 20) | Disposition |
|---|---|---|---|
| 1 | Integrations & interoperability | 1 (Boltline) | Extended — connector engines/catalog are a gap; the claim is at managed-object list weight |
| 1 | Inspections & field operations | 1 (IVM SmartHub) | Core (inspection records) — the claim is at use-context list weight (see core-boundary decision) |
| 3 | Program & project operations | 0 | Core |
| 3 | Operational data & structured records | 0 | Core |
| 3 | Workflow automation | 0 (1 raw hit removed: name-only token) | Core (registry) — execution Extended |
| 3 | Reporting & operational intelligence | 0 | Extended (engine) |
| 3 | Asset & equipment management | 0 | Core |
| 3 | Workforce & mission readiness | 0 | Extended |
| 3 | Safety & compliance management | 0 | Extended |
| 3 | Governance & compliance functions | 0 | Extended |
| 3 | Authorization & access services | 0 (6 raw hits removed: boundary/status class) | Extended |
| 3 | Common security services | 0 | Extended |
| 3 | Network connectivity & platform services | 0 | Extended |
| 3 | Usage information & metering | 0 | Core |
| 3 | Policy enforcement | 0 | Extended |
| 3 | Application configuration & deployment | 0 | Extended |
| 3 | Mobile capabilities | 0 | Extended |
| 3 | AI capability | 0 | Extended |
| 3 | Contractor & vendor management | 0 | Core |

The two standing claims, with their evidence weight stated plainly:

- **Boltline — `integrations`.** "Federal customers use Boltline to
  manage engineering-to-production workflows, including parts, bills
  of materials, inventory, work plans, orders, integrations,
  attachments, and auditable workflow activity." The token names a
  class of object the offering itself manages, in the same list as
  parts and orders it plainly manages — not a name, not a status, not
  third-party. It stands at list weight, and under the standing
  disposition it buys no core function.
- **IVM SmartHub — `inspections_field_ops`.** "Whether supporting IT
  service delivery, field operations, onboarding, break/fix
  replacement, or controlled equipment distribution, IVM SmartHub
  delivers a smarter, more secure, and more efficient way to manage
  access across the IVM Smart Solutions ecosystem." A use-context
  list — the same list weight as the founding group's own TrackVia
  `field operations` evidence. The fork's deeper substance ("automated
  tracking and chain-of-custody workflows for IT assets") matches no
  family and is a named near-miss, not a second claim.

## Core-boundary decision

**Stated once:** in this set, **no core function is claim-supported.**
The sole Core-disposition claim (`inspections_field_ops`, IVM) stands
at use-context list weight, and the sole other claim (`integrations`,
Boltline) is Extended under the category's standing dispositions. The
founding Operations Management substrate (12 functions, below) is
carried whole as the category's merged records machinery and
re-anchored to tier null — carried, not claimed. The justification is
the one the census itself supplies: these 20 forks are in this
category because their own descriptions describe operational work —
maintenance, assets, field execution, logistics, facilities — not
because their vocabulary matches the founding pair's phrases. The
substrate holds the records of that work (work orders, inspections,
assets, usage); the engines the forks actually differentiate on are
registered as gaps, by name, below.

## What the build does (the carried substrate, 12 core functions)

The founding group's core, carried whole (see the README's
byte-identity accounting: 7 of 7 `src/opsmgmt/` modules byte-identical
to `groups/operations-management-l2/src/opsmgmt/`):

1. **Directory** — people and organizations keyed by opaque external
   references; references are never resolved to real identifiers.
   IA-2 stays with the embedding organization (gaps).
2. **Projects** — a project belongs to exactly one organization;
   people join as members with roles.
3. **Assets** — assets belong to organizations, sit under projects,
   and carry a lifecycle status.
4. **Work orders** — work orders belong to projects and assets;
   status is a managed lifecycle, and **overdue is derived at read
   time, never stored**, from `due_at` and status through the single
   seam `OpsStore._is_overdue` (the negative-control drill target).
5. **Inspections** — immutable once recorded; outcomes stored
   verbatim as supplied; **no score is computed**.
6. **Usage records** — quantities are integers (floats and bools are
   rejected at the boundary); sign is unconstrained (a negative
   quantity is a reversal); records are immutable.
7. **Workflow registry** — versioned automation definitions are
   registered and versioned; **the registry never executes them**
   (execution is Extended, pinned by tests).
8. **Reports** — counts over the substrate (work orders, overdue
   derived at the requested instant, inspections, usage totals).
9. **Search** — across projects, assets, work orders, and
   inspections.
10. **REST API** — JSON over HTTP (stdlib `http.server`), default
    port 8797.
11. **RBAC** — a fixed 16-action matrix over three roles
    (admin / operator / viewer); `workflow_write` and `audit_read`
    are admin-only.
12. **Audit log** — append-only, records **denied** attempts as well
    as permitted ones; the store refuses update and delete on audit
    entries.

## Documented control claims

Control families the set's own descriptions assert, traced to the
claiming fork and its sentence. Two tiers, kept separate: the
**standing claims** above carry no control language at all (neither
`integrations` nor `inspections_field_ops` asserts a control), so
everything below is **prose-level** — assertions recorded at their
stated weight, never promoted to taxonomy claims. Assertions inside
removed boundary/status prose do not count (Rohirrim's "identity
plane", named inside its authorization-boundary sentence, is the
recorded example), and neither do inherited-platform assertions
(COMPASS inheriting Azure Government's controls; USU's work resting
on its host provider's compliance posture). Weights are stated where
an assertion is a list item, a catalogue line, or readiness/records
prose rather than a direct statement.

- **IA — Identification and Authentication: documented by 4 forks.**
  MaintainX: "role based access via a dedicated fed only identity
  provider with CAC/PIV support" (one item in its security-measures
  list sentence). COMPASS: "DoD Common Access Card (CAC)
  authentication, utilizing X.509 certificates, ensures secure access
  for users."; and "The back-end administrative access is protected
  through Remote Desktop Protocol (RDP) and Duo Federal multi-factor
  authentication (MFA) using FIPS 140-2 validated hard token
  YubiKeys." Partos: "It supports multi- and single-tenancy, multiple
  IdPs and SSO, SCIM provisioning, and granular role-, group-, and
  permission-based access." CARTN: "Access to the portal and
  underlying infrastructure is protected by multi-factor
  authentication."
- **AC — Access Control: documented by 4 forks.** COMPASS: the
  platform "enforces role-based access control (RBAC) policies for
  both administrative staff and customer users." Partos: "granular
  role-, group-, and permission-based access" (sentence above) and
  "Access is dynamically controlled based on variables like
  nationality and geographic location, ensuring continuous compliance
  at every layer." Globality: "Authenticating and authorizing users
  to ensure access is strictly controlled" (a clause of its
  procurement task-list sentence). CARTN: "All components are hosted
  in a cloud environment with network-level controls that limit
  connectivity to authorized services only."
- **SC — System and Communications Protection: documented by 3
  forks.** Globality: "all user data is encrypted at rest, in
  transit, and fully protected throughout its data lifecycle."
  MaintainX: "end to end TLS 1.2+ encryption" (an item in its
  security-measures list sentence). Silkline: "Two-way encryption"
  (an item in its platform feature list — feature-list weight).
- **CA — Security Assessment and Authorization: documented by 3
  forks.** MaintainX: "vulnerability scanning" and "configuration
  drift detection" (items in its security-measures list sentence).
  COMPASS: "Security Content Automation Protocol (SCAP):
  Configuration compliance scanning" (a line in its external-services
  catalogue — catalogue weight; the same line's "Automation" token is
  the removed name-only hit above). Partos: "compliance monitoring
  across ITAR, EAR export controls, and DFARS" (in its
  supplier-vetting sentence — monitoring of suppliers against export
  and contracting regimes).
- **AU — Audit and Accountability: documented by 2 forks, both at
  records/readiness weight.** Boltline: "audit logs" are among the
  data it may store (its data-categories sentence). IVM SmartHub:
  the system improves "audit readiness" (its access-management
  sentence).
- **CM — Configuration Management: documented by 1 fork.**
  MaintainX: "container hardening (CIS/STIG baselines)" (an item in
  its security-measures list sentence).
- **SI — System and Information Integrity: documented by 1 fork.**
  MaintainX: "malware scanning for uploaded files" and "continuous
  monitoring and anomaly detection" (items in the same sentence).

**Not documented by any fork in this set:** AT (Awareness and
Training), CP (Contingency Planning), IR (Incident Response), MA
(Maintenance), MP (Media Protection), PE (Physical and Environmental
Protection), PL (Planning), PM (Program Management), PS (Personnel
Security), RA (Risk Assessment), SA (System and Services
Acquisition). These are listed as not documented, never filled from
a baseline — this set has no baseline to fill from. (Tansi's "incident
reporting and corrective actions" is field-operations reporting in
its platform feature list, not an incident-response control
assertion, and is not counted under IR.)

## Named absences

Beyond the empty families, the following checked absences are named
because the forks' substance makes them conspicuous. Each stands;
nothing was back-filled.

- **Asset management, the signature absence (0 of 20 claimed, 6+
  forks in substance).** The family's pattern needs the founding
  phrase "asset and equipment management". AtomAI (a full CMMS:
  "real-time asset intelligence across complex operational
  environments"), IVM (chain-of-custody asset workflows), BitRip (QR
  asset tracking), NEXGEN ("comprehensive asset, work order, and
  maintenance management"), USU (IT asset management incl.
  discovery), and CARTN (asset tracking and locating) all assert
  asset management in substance; none carries the phrase. The
  set's centre of gravity is asset/maintenance operations, and the
  standing taxonomy records none of it.
- **Scheduling & rostering (no family; substance in at least 3
  forks).** MaintainX ("preventive maintenance scheduling"), Fulcrum
  (production scheduling inside its ERP/MRP/MES description),
  DepotFinity ("smart scheduling"), with report scheduling in a
  fourth (COMPASS's scheduled report notifications) — the founding
  group's named absence, inherited unchanged, now with a larger
  substance count than the tiered groups ever had.
- **IoT / telematics data collection (no family; substance in 2
  forks).** CARTN (continuous GPS/RFID asset tracking and locating)
  and SignifiVISION (centralized monitoring and status for deployed
  kiosk/locker devices) — the founding group's other named absence.
- **Workforce readiness, half-phrased (0 of 20).** Tansi asserts
  "workforce readiness and performance"; the pattern needs
  "workforce and mission readiness". One fork, half a phrase.
- **Policy enforcement, verb-adjacent (0 of 20).** Partos
  "automatically enforce data access boundaries" and COMPASS
  "enforces role-based access control (RBAC) policies" both carry
  enforcement substance; the pattern needs the literal "enforce
  policy". The substance is recorded under AC above, not claimed.
- **AI capability, scoped-phrase absence (0 of 20).** Five forks are
  *filed* under Artificial Intelligence (AI) and several more assert
  AI substance (Fulcrum's Archie and AI models, Partos's AI-native
  platform, NavigatorCRE's natural-language querying); none carries
  a scoped phrase ("artificial intelligence" / "machine learning" /
  the joint integrations-and-AI pattern). AI branding is not a
  claim, exactly as the founding group scoped it.

## Gaps registered for this set

Following the repo's gap-batch rule, these are named here and roll up
into the root `GAPS.md` when the parent ships this set; they are
worked as one final batch after the last group.

Standing category gaps (inherited from the founding group, restated
because this set's forks lean on them): workflow automation execution
engine; real-time intelligence & analytics engine; AI models;
low-code application builder & deployment engine; integration
connector engines & catalog; mobile applications & offline sync;
network connectivity services & cloud platform operations;
authorization service / identity provider (IA-2 stays with the
embedding organization — this set's prose documents CAC/PIV, MFA, SSO,
and SCIM assertions by four forks, none of which the build provides);
common security services enforcement plane; policy enforcement plane;
governance/compliance console engine; scheduling & rostering; IoT /
telematics data collection; multi-tenant hosting (the build is a
single-tenant reference implementation); encryption at rest (a
deployment-layer concern; the build implements no cryptography of its
own); TLS in transit (terminated by deployment configuration);
identity proofing and credential issuance behind the documented
CAC/PIV and MFA assertions.

Set-specific gaps (this set's forks' own engines, by name):

- **CMMS / enterprise asset management depth** — computerized
  maintenance management and EAM execution (AtomAI, NEXGEN, USU):
  asset discovery, preventive-maintenance programs, chain-of-custody
  workflows.
- **Manufacturing execution & ERP/MRP** — Fulcrum's and Boltline's
  production layer: MRP, MES, bills of materials and work-plan
  execution, production scheduling.
- **Procurement & sourcing platforms** — Globality, Tarly Cowork,
  Silkline, Rohirrim: sourcing orchestration, market research,
  supplier discovery/vetting/matching, quote and order collaboration.
- **Contract execution management** — COMPASS and Tarly Cowork:
  contract surveillance, acquisition-workflow execution, obligation
  tracking (distinct from the Contract Management L2 group's records
  substrate).
- **EV charging network management** — IVM's second line: charging
  infrastructure operations.
- **Real-estate & facilities portfolio platform** — NavigatorCRE:
  lease administration, space planning, portfolio data aggregation.
- **Kiosk & locker access management** — SignifiVISION and IVM's
  SmartHub networks: unattended self-service device administration,
  access-controlled distribution.
- **AI assistants & agents** — Fulcrum's Archie, Rohirrim's
  retrieval-based AI platform, NavigatorCRE's natural-language
  querying: the assistant layer five AI-filed forks describe and no
  scoped phrase claims.
- **Supply-chain risk & payments orchestration** — Partos's
  onboarding/vetting/screening and settlement layer; Silkline's
  supply-chain collaboration and risk notification layer.

## Coverage statement

20 of 20 forks in census unit `untiered:Operations Management` are
spec'd in `specs/specs.json`; membership is pinned by tests against
`remainder.json`. Claims: 2 total (integrations 1, inspections &
field operations 1), each with verbatim evidence. Zero-claim forks:
18 of 20, reported plainly. Tier: null on every sheet; no baseline
asserted; no CMMC equivalence drawn. All counts are a floor over the
cached source text — for Concourse the cached description is visibly
truncated mid-listing, and its floor is a floor over an incomplete
listing (recorded in `scratch/ARTIFACTS.md`).

