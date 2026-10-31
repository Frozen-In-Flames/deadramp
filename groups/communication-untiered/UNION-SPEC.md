# Union Spec — Communication, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set**: **2 forks**, category
**Communication**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes no
baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's union
spec carries.

Membership is exactly census unit `untiered:Communication` in
`../../remainder.json` (2 fork IDs, verified mechanically). In
`forks.json` both forks are filed "Uncategorized (none in source)";
the census assigned both to this category from their own
descriptions, and the spec sheets record the assignment. Both
forks' recorded authorization status is FedRAMP In Process — a
status is record data, not a claim.

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

**Paired record, kept separate:** F1302271924A — the same AtHoc
product's "- High" record, filed under Collaboration at CMMC
L3-adjacent — is a separate registry offering per the Phase 1 rule
that paired records stay separate. It is not a member of this set,
and nothing in its record is attributed to this set's fork
(F1302271924), whose own record says impact Unknown. Pinned by
test.

## How functions were counted

The category's fixed 21-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../communication-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 21 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 10 of 10 forks, 52 of 52 claims, deep-equal** against
the sheets at the original ship commit (`192690d`) — using the
parent's sentence split and evidence rule (sentence split after
the founding normalization, carriage returns to spaces; first
matching sentence; over 400 characters, truncated to 397 + '...').

The raw pass over this set produced **5 hits**; **2 were removed**
in the adjudication pass as applications of the founding group's
recorded correction *classes* (its implemented fixes are embodied
in the patterns and were not altered; see `scratch/ARTIFACTS.md`):

- `scheduling_events` (AtHoc) — removed under founding correction
  class 5: the matched "events" are incident events ("critical
  events"; "report events"), the class removed for Everbridge;
  not scheduled-event or check-in management.
- `reporting_analytics` (AtHoc) — removed under founding
  correction class 3: the matched "reporting" is "self-reporting
  by individuals", framed by its own sentence as an input to
  personnel accountability; user-side reporting as a system input
  is not reporting provided by the offering.

An exclusion pass scanned every standing hit's evidence sentence
for scope-exclusion phrasing and third-party catalogue segments:
**no further hits were removed** — no standing evidence sentence
carries scope-exclusion phrasing, and neither fork's
`certified_services` record field was read or matched (both are
empty lists in the source). Final result: **3 claims across the
set; both forks carry at least one claim** — there is no
zero-claim fork in this set, and the count is a floor, not a
ceiling.

Census citations: 2 citations are recorded for these forks in the
census (one per fork); **2 of 2 verify** as verbatim substrings of
the forks' own descriptions, and **0 of 2** are themselves a claim
evidence sentence — both are the forks' opening positioning
sentences, which tag nothing. Verification is not a claim, in
either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 2 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Notifications, alerting & critical-event communications | 1 (AtHoc) | **Core** (templates, dispatch, scheduling) |
| 1 | Email & messaging channels | 1 (Cisco) | **Core** (composition + delivery records) |
| 1 | Voice, telephony, IVR & contact center | 1 (Cisco) | Extended (media + conversation engines; the delivery records the calls presuppose are Core substrate) |
| 4 | Delivery verification, receipts & acknowledgements | 0 | **Core** (receipts + ack tracking) — **zero claimants in this set; carried, not claimed** |
| 4 | Contacts, directory & constituent management | 0 | **Core** (directory) — **zero claimants in this set; carried, not claimed** (substance present, see Named absences) |
| 4 | Identity proofing, login & access control | 0 | **Core** (RBAC; identity products Extended) — **zero claimants at family level in this set; carried, not claimed** (access prose recorded at the prose tier below, not converted to a claim) |
| 4 | Audit logging & trails | 0 | **Core** (append-only audit log) — **zero claimants in this set; carried, not claimed** |
| 4 | Reporting, dashboards & analytics | 0 standing | Core (records/ack-status substrate); engines Extended — **the set's sole raw hit was removed (correction class 3); carried, not claimed** |
| 4 | Scheduling, events & check-in | 0 standing | **Core** (send-at scheduling) — **the set's sole raw hits were removed (correction class 5); the function's claim support here rests on the notifications family, whose Core disposition covers scheduling** |
| 4 | Search, eDiscovery & FOIA | 0 | Core (search over records); eDiscovery production Extended — **zero claimants in this set; carried, not claimed** |
| 4 | Email security, anti-phishing & threat protection | 0 | Extended (detection engines) — zero claimants in this set |
| 4 | AI/ML analysis & virtual assistance | 0 | Extended (models) — zero claimants in this set |
| 4 | Communications archiving, retention & records management | 0 | Extended (archiving engines; immutable records are Core) — zero claimants in this set |
| 4 | Correspondence & casework management | 0 | Extended (casework depth) — zero claimants in this set |
| 4 | Secure & encrypted transmission | 0 | Extended (E2E transport; channel config is Core) — **zero claimants in this set** ("securely" is an adverb in the only candidate sentence; see Named absences) |
| 4 | Key & certificate lifecycle management | 0 | Extended (CA automation) — zero claimants in this set |
| 4 | Workflow & business process automation | 0 | Extended (engines) — zero claimants in this set |
| 4 | Personnel/asset tracking & situational awareness | 0 | Extended (device/location platform) — **zero claimants in this set; substance present (location/status visibility), phrase absent** |
| 4 | Permits, passes, surveys & forms | 0 | Extended (domain system) — zero claimants in this set |
| 4 | Electronic signature | 0 | Extended (signature execution) — zero claimants in this set |
| 4 | Payment processing | 0 | Extended (payment rails) — zero claimants in this set |

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's twelve-function substrate **whole** — directory;
channels; templates; message composition; delivery records;
dispatch & receipts; scheduling; acknowledgement tracking; records
& search; REST API; access control (RBAC); audit log. The
substrate is records machinery that every sibling's output
presupposes, and it is tier-independent code: the founding source
contains no tier or baseline machinery, so there was nothing
tier-shaped to strip. Claim support in **this set** is stated
plainly, function by function:

- **Claim-supported (5):** templates, message composition,
  delivery records, and dispatch — via Cisco's `messaging` claim
  (Core disposition: composition + delivery records) and AtHoc's
  `notifications_alerts` claim (Core disposition: templates,
  dispatch, scheduling); and scheduling — via the notifications
  family's Core disposition, the `scheduling_events` family's own
  raw hits in this set having been removed as incident-event
  artifacts (correction class 5). Dispatch's receipts are records
  the substrate keeps; the receipts-and-acknowledgements *family*
  (`delivery_verification`) has no claimant in this set.
- **Carried, not claimed (7):** directory (its family has 0
  claimants here, substance notwithstanding), channels (channel
  configuration is substrate with no taxonomy family, exactly as
  in the founding build), acknowledgement tracking (its family
  has 0 claimants here), records & search (its family has 0
  claimants here), REST API (substrate surface, no family), RBAC
  (its family has 0 claimants here; access prose is recorded at
  the prose tier of the Documented control claims section and is
  not converted to a claim), and the audit log (its family has 0
  claimants here).

Functions are **carried** as substrate; no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/comm/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `comm` under `src/`, ids sequential per object type
with fixed prefixes (`ct-`, `grp-`, `ch-`, `tpl-`, `msg-`,
`dlv-`), failed operations consume no id and change nothing, all
timestamps UTC ISO-8601, roles `admin|operator|viewer` with the
founding permission matrix, permission checked before any state
change or id allocation at the store layer and again at the
service layer, message and delivery records immutable once
written, and the audit log append-only with denied attempts
recorded. Where the founding contract's text ties the RBAC and
audit functions to "the L2 baseline", read it here as
**baseline-neutral substrate**: at tier null they are carried as
the parent design carries them, claimed against no baseline.

The category's **transport discipline** is preserved exactly, as
the founding build implements it: dispatch goes through a
**reference transport** — a deterministic stub that marks a
delivery `delivered` with a receipt labelled
`reference_transport: true` when an enabled channel of its kind
exists, else `failed` with `failure_reason='no_enabled_channel'`.
It transmits nothing over any real network: no email is sent, no
SMS is sent, no call is placed, no push notification is pushed.
The send gate is the category's signature invariant, and it is
what this tree's negative control mutates (see `tests/README.md`).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Control areas **documented in part** by at least one fork in the
set, at the prose tier (control language in sentences that fired
no taxonomy family, traced and quoted, never converted to
claims):

- **Access control (AC), in part** — **2 forks**, at prose
  weight. BlackBerry AtHoc (F1302271924): "AtHoc Connect empowers
  organizations to create their own permission-based network to
  establish interoperable communication and information sharing
  with organizations in their community" — a permission-gated
  network asserted in the fork's own words. Cisco UCM Cloud
  (F1604017885): "create personalized access lists, and give
  access to all your corporate collaboration features from mobile
  phones using Webex App or Cisco Jabber" — per-user access lists
  asserted in the fork's own words. Neither sentence carries the
  `identity_access` family's phrases, so the family stands at
  0 of 2 in the claim table; this prose-tier record does not
  change that.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, AU, CA, CM,
CP, IA, IR, MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI **as
control claims** — is asserted by no description in the set. In
particular:

- **Identification & authentication (IA)** — no description
  carries a login, authentication, SSO, or identity-proofing
  phrase. AtHoc's "personnel accountability" is accountability
  for personnel status, not authentication of users.
- **Cryptographic protection (SC)** — no description asserts
  encryption. AtHoc's "communicate and collaborate securely" is
  an adverb, and its "safeguards important personal information"
  is safeguarding prose with no encryption or control-framework
  language; Cisco's "government-level security" is posture
  prose. All three are recorded here so the record shows they
  were read; none is documented as a control claim.
- **Audit (AU)** — no description carries audit language in any
  form.

If the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **Video conferencing, meetings & real-time media — no family
  exists.** This category's standing absence (0 of 10 in the
  founding group; 0 of 7 at L3-adjacent) stands here against the
  most video-heavy description the category has produced: Cisco
  UCM Cloud is a voice-and-video platform ("Voice and Video
  Calling", "immersive video rooms", "Webex Meetings technology",
  "Conferencing", "desktop sharing"), and the taxonomy tags its
  voice and its messaging but has no family for its video, its
  meetings, or its presence. Recorded, not repaired; the video
  half is a gap below.
- **Delivery verification, receipts & acknowledgements — 0 of
  2.** Neither description contains "acknowledg" in any form.
  AtHoc's substance is acknowledgement-shaped — personnel
  accountability assembled from manager inputs, call-center
  inputs, HR/travel data streams, and self-reporting — but the
  family's phrases ("deliver and verify", verified messages,
  acknowledgements) never occur.
- **Personnel/asset tracking & situational awareness — 0 of 2,
  substance present.** AtHoc Account "enables real-time
  visibility into location and status" and Collect gathers "rich
  geo-tagged media"; the family's phrase "location data" never
  occurs and no tracking phrase fires (the founding correction 4
  scoping). Recorded, not repaired.
- **Contacts & directory — 0 of 2, substance present.** AtHoc's
  accountability registry (inputs from managers, HR and travel
  systems) and Cisco's "find the right people" are directory
  substance in wording no family phrase reaches.
- **Identity & access at family level — 0 of 2.** See the
  Documented control claims section: access prose exists at the
  prose tier in both forks; the family's phrases occur in
  neither.
- **Audit logging — 0 of 2.** No audit wording in either
  description; the Core audit log is carried substrate only.
- **Secure & encrypted transmission — 0 of 2.** "Securely" is
  the set's only candidate token (see N4 in
  `scratch/ARTIFACTS.md`).
- **Scheduling & reporting families — 0 standing, by removal.**
  Both families' sole raw hits in this set were removed under
  the founding correction classes (R1–R2 in
  `scratch/ARTIFACTS.md`); the absences are recorded here so the
  removals are visible in the ranking, not silent.
- **Presence — no family.** Cisco Jabber and Webex presence
  ("see if and how they are available") is a named absence of
  the same kind as video: substance present, no family.
- **The remaining families — 0 of 2 each, no substance note:**
  email security, AI/ML, archiving & records, search &
  eDiscovery, correspondence & casework, key & certificate
  lifecycle, workflow automation, permits & surveys,
  e-signature, payments. ("Permission-based" is not "permit";
  "call center operators" is not "contact center".)

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
restated here only where this set's forks claim or substantively
describe them (counts are this set's):

- [ ] Video conferencing, meetings & real-time media transport engines (Cisco substance throughout; 0 taxonomy claims — no family exists)
- [ ] Voice/telephony media, call-control & endpoint interoperability engines (Cisco, 1 claim at records weight; the media itself is not built)
- [ ] Presence & availability services (Cisco substance; no family)
- [ ] Desktop sharing & collaboration content sharing (Cisco substance)
- [ ] Crisis-communication orchestration & multi-channel alerting engines (AtHoc, 1 claim; alerting execution and campaign engines are not built — dispatch of composed messages through the reference transport is Core)
- [ ] Personnel accountability, location/status visibility & field-reporting platform (AtHoc substance; its family stands at 0)
- [ ] Inter-organizational federated communication networks (AtHoc Connect substance)
- [ ] Voicemail & unified messaging engines (Cisco substance beyond the messaging records claim)
- [ ] Real channel transports — email/SMS/voice/push carrier and provider integration (the build's transport is a labelled reference stub, never a real channel)
- [ ] Platform layer: encryption at rest (deployment layer); TLS only when a certificate is configured; multi-tenancy (the build is a single-tenant reference deployment); demo identities are hooks, not an IdP — IA-2 stays with the embedding organization

The founding group's remaining extended gaps (email-security and
AI/ML engines, archiving/eDiscovery engines, casework depth,
key/certificate automation, end-to-end encrypted transport,
tracking platform depth, permits/payments/e-signature engines,
workflow/BPM and reporting/analytics engines) are already
registered under the parent group and are not re-registered here.

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Communication`; 3
taxonomy claims tagged from the forks' own descriptions (5 raw
hits, 2 removed under the founding group's recorded correction
classes; both forks claiming at least one); the twelve-function
substrate carried byte-identical from the founding Communication
L2 build and re-anchored to tier null; tier null recorded on
every sheet and pinned by tests. Nothing in this build claims a
FedRAMP authorization, a CMMC certification, or a control
baseline for any fork or for the build itself.
