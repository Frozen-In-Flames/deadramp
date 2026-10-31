# Addendum — Mobile Device Management (MDM), CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the
1 previously uncategorized fork of remainder build unit
**`addition:mobile-device-management-l2`** (see
`../../REMAINDER.md`). The original union spec stands as
written: its taxonomy, its 14-function core, its Moderate
control baseline, and its core-boundary decisions are
**unchanged**. This document records what joined, what the
newcomer claims under the group's existing taxonomy (nothing),
the core-delta decision — including the one extension candidate
considered and decided against, stated head-on in §3 — and the
updated union statement.

**Headline: forks spec'd 1 / 1; 0 new claims — a zero-claim
fork; core delta — zero functions extended, `src/`
byte-identical (the device-registry question was considered
and decided, §3, not silently defaulted); tests 75 → 89, all
passing.** The category's five named absences meet their first
genuine MDM description: **two retire in substance**
(enrollment & provisioning; app & content delivery), **one
splits** (policy enforcement asserted, policy management not),
and **two survive in both senses** (remote wipe/lock; device
location) — every one of them survives at claim level, because
this taxonomy contains no device-management family for any of
them to claim. **2 new gap functions** are named in §5, and 3
already-registered gaps gain a member by substance.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1507116930` | Ivanti / Ivanti Neurons for MDM (Formerly MobileIron) |

Census membership was verified against `remainder.json` before
building (unit `addition:mobile-device-management-l2`,
`fork_ids == ["F1507116930"]`, `extends_group ==
"mobile-device-management-l2"`). The fork is FedRAMP
**Moderate** / Certified, SaaS, Government Community Cloud, so
the group stays single-tier and the Moderate baseline is
inherited in full (Merge Rules 1–2), unchanged. `forks.json`
files the fork "Uncategorized (none in source)" and its own
source record carries `business_categories []`; the DeadRamp
category is the census proposal, Mobile Device Management
(MDM), recorded on the sheet as such. A filing label (or its
absence) is not a functional claim either way — the founding
fork's own correction 7, applied symmetrically.

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast`** (parsed, never executed,
  never re-typed), asserts the taxonomy's 16 (id, label,
  pattern-list) triples, and re-applies the original sentence
  splitting (bullet-aware, then sentence-final periods),
  case-insensitive substring matching, and **last-match**
  evidence rule. Before tagging the newcomer, the extractor
  **reproduces the original fork's shipped claim table
  exactly** from the cached description — NiOS: all 16
  families, evidence sentences included, deep-equal — and
  asserts the original sheet deep-equal to git HEAD. The new
  sheet is **appended** to `specs/specs.json`; the original
  sheet is byte-preserved through its closing brace (asserted
  in the extractor).
- The original extractor records its wording-artifact
  corrections as prose in its docstring and in
  `scratch/ARTIFACTS.md` (no CORRECTIONS literal exists); they
  were applied by the same reasoning, and the mechanical ones
  are asserted in the extractor: only `service_desc` is
  matched; no hosted-services exclusion is invented (the
  newcomer's `certified_services` is empty and no
  scope-exclusion segment exists — asserted); a category label
  earns no tag; and the founding fork's correction 2 is applied
  in reverse — there, "mobility" named telecom services and
  earned no device tag; here the surrounding vocabulary *is*
  device vocabulary, but tags still follow the taxonomy's
  pattern phrases only, and substance without a family is
  registered as gaps, never rounded into a claim.
- Exclusion discipline, checked not assumed: the description
  contains no catalogue of third-party hosted applications and
  no scope-exclusion segment. Its operating-system list (iOS,
  Android, Windows 10, macOS, Zebra, Oculus) enumerates the
  platforms the fork's own product manages — its own supported
  surface, not a third-party catalogue. Matched text is the
  full text; the raw hit count is zero, so **no raw hit was
  removed**.
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID via
  `ProductsMap` (the original extractor's join). The
  description was present; no live fetching. Descriptions are
  stored whitespace-normalized to single spaces, the group's
  original convention (asserted against the shipped sheet).
- The census starting point was verified, not trusted: the
  fork's **2 census citations** were re-checked against its
  stored description and **both verify verbatim**. Both tag
  no family (see §2): verification ≠ claim, and census
  classification ≠ claim either, in both directions.

## 2. What the addition claims

**0 claims.** The newcomer's marketplace description (2,345
characters, 13 sentences under the group's splitter — one of
them the bare "." fragment the source's "console. . When"
double period produces, recorded as a source-text artifact and
tagging nothing) is a genuine mobile-device / unified endpoint
management description. Its functional vocabulary, in its own
words: a "zero trust security platform" that "validates the
device"; "automatically provisions enterprise settings such as
Wi-Fi and VPN"; "applications and content delivery for both GSE
and BYOD programs"; a UEM platform that "incorporates identity,
context, and privacy enforcement to set the appropriate level
of access"; "the simplest onboarding"; and a threat-defense
offering that "continually detects and remediates against known
and unknown (zero-day) device, network and app-level threats".

Under the taxonomy applied verbatim it produces **0 raw hits
across all 16 families** — the mirror image of the founding
fork. The taxonomy was defined from NiOS's telecom expense
management prose (ordering, inventory, bills, budgets,
chargebacks); it contains **no device-management family at
all**, so a description that is device management through and
through has nothing to fire. There is nothing for the
wording-artifact corrections to correct and nothing was
manufactured. The census classified the fork to MDM by
substance ("Unified endpoint / mobile device management") and
that classification is recorded on the sheet as the census
proposal; the claim pass reads the same text for the taxonomy's
pattern phrases and finds none. Both statements are true at
once, and the difference between them is the group's discipline
working as designed — the same discipline that refused, in the
founding fork, to round the word "mobility" up into the device
surface this fork actually describes.

Group claim counts after the addition (2 forks): the total
stays **16** — every family at exactly **1 of 2**, all from
NiOS.

### The five named absences, against the newcomer

The union spec recorded the category's signature surface as
named absences, because the founding fork's description
contained no device vocabulary at all. The newcomer's
description is the first text in this category that speaks
that vocabulary, so each absence is re-checked against its own
words (token-level pins in `tests/test_additions.py`):

1. **Device enrollment & provisioning — RETIRES in
   substance.** "MobileIron technology automatically
   provisions enterprise settings such as Wi-Fi and VPN…"
   (sentence 3); "the simplest onboarding" (sentence 8);
   "Deployment and activation of MTD on mobile devices is
   accomplished silently on managed and unmanaged devices"
   (sentence 11). The word "enroll" never appears, but
   provisioning and onboarding are named in the fork's own
   words. The absence survives at *claim* level — no taxonomy
   family exists for it — and the registered gap gains a
   member by substance (§5).
2. **Remote wipe / lock — SURVIVES in both senses.** No
   "wipe" token, no "lock" token, anywhere in the description.
   The fork's remediation vocabulary belongs to its threat
   defense (sentence 10) and is booked there, not rounded into
   a device-command plane the text never names.
3. **Device policy management & compliance enforcement —
   SPLITS.** No "policy" or "policies" token appears, and no
   policy *management* (authoring, distribution, versioning of
   device policies) is described: that half survives. The
   *enforcement* half is asserted in substance: the UEM
   platform "incorporates identity, context, and privacy
   enforcement to set the appropriate level of access to data
   and services" (sentence 6), and the zero-trust approach
   "validates the device, to ensure that only authorized
   users, devices, apps, and services can access business
   resources" (sentence 1). Booked once, under the registered
   policy gap, with the per-request validation machinery
   registered separately as the zero-trust gap (§5) — two
   distinct Extended functions, no claim counted for either.
4. **Mobile application management — RETIRES IN SUBSTANCE for
   the delivery half.** "…secures corporate email and email
   attachments, applications and content delivery for both GSE
   and BYOD programs" (sentence 3): application and content
   delivery is asserted in the fork's own words. The
   management plane around it — catalog, distribution policy,
   wrapping — is not described ("catalog" token absent,
   "app management" phrase absent) and that half survives.
5. **Device location & tracking — SURVIVES in both senses.**
   No "location", "gps", or "track" token anywhere. The fork
   manages devices across a "global mobile workforce" without
   ever claiming to locate one, and none is attributed to it.

### Near-misses, itemized

The taxonomy families the description comes closest to (the
full sentence map is `scratch/additions_sentence_map.json` —
13 sentences, every hit list empty):

- **`lifecycle_single_view`** — sentence 6: IT departments
  "securely manage their global mobile workforce from a single
  console." The verbatim patterns are "single-pane window" and
  "telecom lifecycle management"; "single console" is neither.
  Recorded, not repaired — the category's third single-view
  phrasing, and the pattern stays as shipped.
- **`cloud_hosting_platform`** — sentence 5: "a cloud-based,
  scalable architecture." The patterns are "hosted on Amazon
  Web Services" and "multi-tenant architecture"; neither
  appears (no "multi-tenant" token at all). The newcomer
  deploys Government Community Cloud where the founding fork
  is Public-of-record prose — hosting is the fork's platform
  layer regardless and transfers nothing to the build.
- **`budget_alerts`** — sentences 10–11 describe continual
  detection and remediation of threats; there is no "system
  alerts" phrase and no "alerts" token of any kind. Detection
  is booked as the threat-defense gap, not as a budget family.
- **`reporting`** — no "reporting" and no "reports" token
  anywhere, despite the compliance framing of sentence 12
  ("helps federal agencies to comply with regulatory
  requirements" is outcome prose about the *customer's*
  posture, not a reporting function of the offering).
- **`inventory_management`, `analytics`, `data_integration`,
  `web_portal`, `api_access`** — no "inventory", "analytics",
  "data integration", "web-based portal", or API token of any
  kind. A device fleet is managed throughout the prose, but
  the *inventory* word — and with it the family's registry
  phrase — never appears; the fleet's records form is the
  core-delta question decided in §3, not a claim.

### Wording artifacts

None. Zero raw hits means no claim stands on an artifact, and
no artifact had to be pinned at reduced weight. The absence of
artifacts is itself recorded because the founding fork's
artifact log (an "optimization" that lived only in a product
name; a "mobility" that named telecom services) shows the
failure modes this fork simply does not present — its product
name says "MDM" outright, and the name is still not a claim.

## 3. Core-delta decisions

The newcomer claims no family, so no family's disposition
changes. The per-family state, for the record (dispositions
from UNION-SPEC's ranking; all 16 claimed by NiOS only):

| Family | Disposition (UNION-SPEC) | Core delta |
|---|---|---|
| Telecom ordering & service orders | Core — order records & lifecycle | **Carried** |
| Built-in customizable workflow | Core slice — registry, never executed | **Carried** |
| Telecom service inventory management | Core — inventory registry | **Carried** |
| Bill validation, reconciliation & verification | Core — bill records & validation runs | **Carried** |
| Bill dispute initiation & tracking | Core — dispute records | **Carried** |
| Financial management | Core — budget/obligation substrate | **Carried** |
| Budget visibility | Core — derived at read, never stored | **Carried** |
| Budget alerts | Core — alert records; delivery Extended | **Carried** |
| Internal customer chargebacks | Core — chargeback records | **Carried** |
| Reporting & spending insights | Core slice — registry summaries | **Carried** |
| Telecom lifecycle management, single-pane view | Core substrate — records/search/API | **Carried** |
| Secure web-based portal | Core substrate — as above | **Carried** |
| Data integration | Extended — integration engine | **Carried** |
| Analytics | Extended — analytics engine | **Carried** |
| APIs | Core — REST API | **Carried** |
| Cloud hosting platform | Platform note | **Carried** |

**The device-registry question — considered and decided.**
This addition was flagged in advance as the live candidate for
the pattern's first non-zero core delta: a genuine MDM fork
might claim device functions whose records form the TEM-shaped
core cannot hold. It does not, and the reasons are stated
rather than defaulted:

1. **No claim requires it.** The newcomer claims 0 of 16
   families. Core extensions in this project are claim-driven:
   a function enters Core when a spec'd claim presupposes its
   records form. The device functions here are asserted in
   substance only, and substance without a claim is registered
   Extended — that is the rule every prior addition followed,
   and bending it for the category's most famous product name
   would be reputation doing the work evidence is supposed to
   do.
2. **The naive form is barred by the group's founding
   invariant.** A device registry is an identifier registry:
   its natural keys are IMEIs, serials, phone numbers, MAC
   addresses. This group's core was built the other way — the
   inventory shape is pinned to exactly ten keys, none of which
   can hold a phone number, IMEI, serial, or any real device
   identifier (UNION-SPEC core function 2; pinned by
   `test_inventory.py`), because the founding fork's estate is
   services, not handsets. Bolting an identifier registry onto
   that core would not extend the substrate; it would repeal
   its privacy discipline.
3. **What the fork describes is planes and engines, not
   records the substrate lacks.** Provisioning pushes settings
   *to* devices; zero-trust validation decides access *per
   request*; threat defense detects and remediates *on*
   devices. Each is an execution surface over live devices —
   Extended by the same reasoning that keeps carrier-side order
   execution Extended in the founding build — not a registry
   the records substrate is missing.

**Result: the core is unchanged**, and the device-management
plane is registered Extended in §5 in full. For the record, so
a future directed build inherits the constraint rather than
rediscovering it: any device-records extension to this group
would have to hold devices by **opaque caller-supplied
references only** — no IMEI, serial, phone-number, MAC, or
location field, the founding invariant carried over — with
device state derived or event-driven under the same discipline
as the substrate's existing derivations. That is a boundary
condition on a hypothetical build, stated here; it is **not**
built, **not** claimed, and **not** part of this addition.
`src/` is byte-identical to the shipped build (all 7 `mdm`
modules SHA-256-verified against the pre-work hash list in
`scratch/additions_src_hashes_before.txt`; `src/mdm/store.py`
remains `8c0c787a…`, the shipped hash, before and after this
addendum's work, the mutation drill included; the full `src/`
diff against HEAD is empty once the drill's `__pycache__` churn
is restored). The tier baseline does not change: same tier by
construction. The founding fork's five core-boundary decisions
stand verbatim.

## 4. Updated union statement

The group now covers **2 forks**, **16 claims** in total, with
**1 of 2** forks carrying claims. The merged build remains the
same 14-function TEM / managed-mobility records substrate —
organizations & membership, service inventory, order lifecycle,
workflow registry, contracts & quotes, bills & validation,
disputes, budgets with derived availability, chargebacks,
alerts, search & summary reporting, REST API, RBAC, append-only
audit — at the Moderate baseline, now spec'd against 2
marketplace offerings instead of 1. The group's character is
now stated against both of the category's shapes at this tier,
and they could hardly differ more: the founding fork is a
telecom expense system filed under MDM that claims the entire
taxonomy; the newcomer is the category's canonical device
management platform, describing the entire device surface, that
claims none of it — because the taxonomy was built from the
first fork's prose and contains no device family. The union
spec's founding sentence survives the addition and is now
doubly evidenced: this spec follows the descriptions, not the
filing. Two of the five named absences retire in substance and
one splits (§2); the device surface they name is registered
Extended in §5 with the newcomer as its first member, and the
substrate — which an operator of either offering shape uses to
hold the estate's service records, orders, and budgets — is
carried whole, unchanged, for both forks.

## 5. Gaps — for the registry at ship

**New gap functions** (2) — both registered from the fork's
described function (its own sentences), **not** from claims:

- **Zero-trust access validation engine** (device validation;
  identity, context, and privacy evaluation; per-request
  access-level decisions — "validates the device, to ensure
  that only authorized users, devices, apps, and services can
  access business resources") — Ivanti. The access *records*
  such decisions leave are the substrate's audit material; the
  validation machinery itself is Extended.
- **Mobile threat defense engine** (continual detection and
  remediation of device, network, and app-level threats,
  including zero-day, on- and off-connectivity, with silent
  deployment/activation on managed and unmanaged devices) —
  Ivanti (MobileIron Threat Defense).

**Existing gaps gaining a member by substance (no claimant):**

- **Mobile device enrollment & provisioning plane**
  (registered in UNION-SPEC from the category's named
  absences) — +1 **by substance**: automatic provisioning of
  enterprise settings (Wi-Fi, VPN), the onboarding surface,
  and silent activation are the fork's own words (§2.1). The
  absence retires as a substance finding and survives as a
  claims absence (0 of 2 at claim level — no family exists).
- **Mobile application management (catalog, distribution,
  wrapping)** — +1 **by substance for the delivery half**:
  "applications and content delivery for both GSE and BYOD
  programs" (§2.4). The catalog/wrapping half gains no member.
- **Device policy management & compliance enforcement** —
  +1 **by substance for the enforcement half**: identity,
  context, and privacy enforcement setting access levels
  (§2.3), booked here once; the per-request validation
  machinery is the separate zero-trust gap above, and the
  policy *management* half gains no member.

**Absences surviving with no member:**

- **Remote wipe / lock / device command plane** — survives:
  zero wipe/lock tokens in the newcomer's text (§2.2).
- **Device location & tracking services** — survives: zero
  location/gps/track tokens (§2.5).

**Explicitly no claimant:**

- **Optimization engine**, **workflow execution / routing
  engine**, **carrier & network integration engines**, **bill
  reconciliation engine**, **budget projection / forecasting
  engine**, **analytics engine beyond registry summaries**,
  **report generation engine**, **alert delivery transport**,
  **web portal / single-pane web application**, **Managed
  Mobility services operations** — all gain no claimant and no
  member: the newcomer's description contains no telecom,
  billing, budget, or optimization vocabulary of any kind
  (token-verified in the additions tests), and its "single
  console" phrasing (§2) does not make it a member of the
  portal gap either — that gap is the founding fork's claimed
  portal surface, and the newcomer's console is its management
  plane, registered with the device gaps above.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the original
  fork's claim table standing exactly, the literal zero-claim
  table and the whole-taxonomy zero-claim set for the
  newcomer, tier fields (including the "Uncategorized (none in
  source)" filing), the description verbatim against the
  cached source under the group's normalization convention,
  census citation accounting, the no-exclusion pin, the
  named-absence token pins, and the near-miss pins (see
  `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests, in its operator shape: a mobility service line
  held in the inventory registry under an opaque ref (exactly
  the pinned ten keys, no device-identifier field) with the
  estate's funded budget deriving obligated / spent /
  available at read; and a provisioning lifecycle in which a
  mobility line's state moves only through fulfilled service
  orders (requester never decider; suspend then restore),
  while registering a workflow definition changes no state.
- **Tests: 75 → 89, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree. Drill (derived
  availability): the `_available_cents` return line in
  `src/mdm/store.py` patched — scoped to the exact line the
  shipped drill record names, occurrence count asserted = 1 —
  to return the bare budget. **89 tests ran, exactly 5
  failed**: the shipped drill's 4 (`test_budgets`
  availability, both derivation-dependent `test_negative_control`
  cases, `test_reporting` summary) plus exactly 1 from the
  additions module (the mobility-estate derivation case),
  tripping as designed. `store.py` was then restored from the
  pre-mutation copy and verified SHA-256-identical to the
  shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
