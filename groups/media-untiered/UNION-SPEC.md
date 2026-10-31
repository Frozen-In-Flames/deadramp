# Union Spec — Media, untiered (DeadRamp Phase 2, Untiered Set 27)

> **UNION-SPEC v1 — 1 fork spec'd under a taxonomy defined from
> its own description; tier null.**
>
> This set is the remainder census's `untiered:Media` unit
> (REMAINDER.md, census commit `dbcdbf9`): the one fork whose
> FedRAMP impact level is "Unknown" in the source and whose
> function is media. **Media has no tiered group anywhere in
> this repo** — no L1/L2/L3 sibling exists to inherit a taxonomy
> or a substrate from — so this set gets the new-category
> treatment (the Contract Management / Storage method): the
> taxonomy is derived from this fork's own description, and the
> core is built fresh in the house architecture.
>
> Tier discipline: the fork records `fedramp_impact_level`
> exactly as the source has it — "Unknown" — and `cmmc_tier:
> null`. No tier is assigned, no CMMC equivalence is drawn, and
> no FedRAMP baseline is asserted anywhere in this set. The fork
> builds to its documented control claims only (the section so
> titled below replaces the baseline section a tiered group's
> union spec would carry).

| Fork | Product | Status | Claims |
|------|---------|--------|-------:|
| FR2218359666 | Haivision Hub for Government (HUB-GOV) (Haivision Systems, Inc.) | FedRAMP In Process | 6 |

**Total: 6 claims across 6 families. Zero-claim forks: 0.**

The registry filed this fork under "Uncategorized (none in
source)" with no business categories at all. Its assignment to
Media is the census's, from its description; the census
classifier note reads "Live video streaming transport service."
The sheet records both the filed category and the census
assignment plainly.

## Taxonomy derivation

The taxonomy was defined from this one description alone, by the
new-category method: read the description in full (three
sentences, 752 characters), define one family per distinct
function the prose actually names, draw each family's patterns
from the description's own phrases. No family was imported from
another category, and no family exists for a function the
description does not name:

- `live_video_transport` — "transporting live streaming video
  from agency networks to other inter- and intra-agency
  destinations", "connecting live streams between agency
  networks and commercial cloud destinations", "this routing".
- `stream_encryption` — "providing AES-256 encryption of live
  streams".
- `service_startup` — "Offering start-up", first item of the
  third sentence's feature enumeration.
- `device_control` — "integrated device control".
- `stream_optimization` — "stream optimization".
- `status_monitoring` — "status & monitoring".

Because the taxonomy is defined from exactly one description,
every count in this spec is a floor over this set only, and the
taxonomy itself is provisional in the honest sense: it is this
set's own, and it becomes the category's taxonomy if tiered
Media forks ever appear — at which point it will be tested
against their prose the way every founding taxonomy here has
been tested against its remainder.

## Function ranking (1 fork claiming, of 1)

| Function | Disposition |
|----------|-------------|
| `live_video_transport` | Core (endpoint, route, and session records) |
| `service_startup` | Core (session start records) |
| `device_control` | Core (device and control-action records) |
| `stream_optimization` | Core (optimization profile records; the engine is Extended) |
| `status_monitoring` | Core (status snapshot records and derived status views) |
| `stream_encryption` | Extended (the cryptography itself; route records carry a stated encryption label only) |

## The merged build — `media`

A fresh core in the house architecture (`src/media/`: errors,
access, audit, store, service, CLI), Python standard library
only. Demo identities are hooks, not an IdP: alice (admin), bob
(operator), carol (viewer).

1. **Organization registry** — tenant records keyed by an
   external reference. Substrate: every other record hangs off
   an organization.
2. **Endpoint records** — the network's nouns: an opaque
   reference, a label, and a kind from a fixed vocabulary
   (agency_network / cloud_destination) — the endpoints the
   transport sentence moves video between. References unique
   per organization and validated to be incapable of holding an
   email address. (Core: `live_video_transport`.)
3. **Route records** — source and destination endpoints of one
   organization (distinct, same organization enforced), an
   optional caller-stated protocol label, and a caller-stated
   encryption label from a fixed vocabulary (aes_256 /
   none_stated). **Route state is derived at read, never
   stored** (live while a session is open on it, idle
   otherwise). (Core: `live_video_transport`; the encryption
   label is `stream_encryption`'s only records trace.)
4. **Stream session records — behind the one-live-session
   guard.** A session records its route and its start moment;
   stopping records the stop moment. **Session state is derived
   at read, never stored** (live while no stop is recorded). A
   route carries at most one live session: a second start is
   refused through the single seam `_check_route_available`,
   records nothing, and consumes no id — the build's signature
   invariant. (Core: `service_startup`, `live_video_transport`.)
5. **Device records** — an opaque reference, labels, an optional
   endpoint of the same organization. No field can hold an
   address, credential, or network identifier for a device.
   (Core: `device_control`.)
6. **Control-action records** — device, action from a fixed
   vocabulary (start / stop / restart / adjust), an optional
   verbatim note, a moment. Records only: recording an action
   sends nothing and changes no device, route, or session —
   pinned by test. (Core: `device_control`.)
7. **Optimization profile records** — a label, settings text
   stored **verbatim, never parsed or executed**, an optional
   route, an enabled flag. The package has no execution entry
   point. (Core: `stream_optimization`.)
8. **Status snapshot records** — a subject (route or device), a
   status word from a fixed vocabulary (up / degraded / down /
   unknown), a moment. (Core: `status_monitoring`.)
9. **Derived status views** — a subject's current status is the
   status word of its most recently recorded snapshot (recording
   order in the store, not caller timestamps), derived at read;
   the network status view gives each route's derived state and
   current status with counts. (Core: `status_monitoring`.)
10. **Search, summary, REST API** — literal substring search
    over the registered metadata; a summary of counts only; the
    store over HTTP (X-User / X-Role headers); denied attempts
    audited with a `:denied` suffix; audit reads themselves
    audited.
11. **Access control and audit hooks** — three-role permission
    matrix enforced on every operation; append-only audit log
    (JSONL optional) recording every mutation.

### Core-boundary decision (stated once)

The merged build implements **records machinery for the claimed
functions, and nothing else**. It holds **records about media,
never media**: no record shape has a field that could hold
video, audio, a stream payload, or a file, and the shapes are
pinned by test. It transports nothing (routes and sessions are
records of a transport service's operation; the transport itself
— protocols, contribution feeds, inter-agency connectivity — is
a gap), it performs **no cryptography of any kind** (the route's
encryption label is caller-stated metadata; `stream_encryption`
is Extended entire, and the build neither performs nor attains
the fork's AES-256 claim), it controls no device (control
actions are recorded, never sent), it optimizes nothing
(profiles record settings text verbatim; the engine is a gap),
and it collects no telemetry (snapshots are the records
telemetry would produce; the probes are a gap). It computes
**no score, rating, quality metric, or latency figure**
anywhere — the description's "minimal latency" is the fork's
outcome prose, and no latency is measured, computed, or stored.
It holds **no money shape at all**: the description states no
fee, price, or budget, so — as with the sibling new-category
builds — no money record was forced into the design. And it
holds **no personally identifying information**: endpoints,
devices, and organizations are opaque references and labels, and
no record can hold a name or an address beyond those labels.

## Documented control claims

*This section replaces the baseline section of a tiered union
spec. With no tier, there is no baseline to inherit; what
follows is only what the fork's own description asserts, traced
to its sentence. A fork's documented control language is its
claim, never this build's attainment.*

**Documented at family weight (1 family):**

- **SC — cryptographic protection / transmission
  confidentiality** — Haivision Hub for Government
  (FR2218359666): "Hub Gov accomplishes this routing while
  adding minimal latency and providing AES-256 encryption of
  live streams." A named mechanism (AES-256) applied to the
  streams in transit, asserted as a property of the offering.
  That is the whole of it: no key-management, validation, or
  FIPS language accompanies it, and nothing further is traced.
  The build performs no cryptography; its route records carry
  a caller-stated encryption label as metadata only.

**Recorded at prose weight (documents no family):**

- "Securely and reliably transporting" (sentence 1): "securely"
  is an adverb. Under the standing precedent (the Communication
  set), an adverb documents no control family; the auditable
  content of the sentence is the transport function.

**Explicit bounds (functions that are not control claims):**

- **Device control is not AC.** "Integrated device control" is
  the product's function — operating field devices — stated
  with no access-control mechanism; it documents no 800-53
  family.
- **Status & monitoring is not CA or SI.** The monitoring named
  is of the product's own streams and devices — its function —
  not control language about the offering's security posture.

**Not documented (every other 800-53 family):** the description
contains no access-control language (token-verified: "access
control" occurs nowhere), no identity or authentication
language (token-verified: "authenticat", "single sign-on", and
"sso" occur nowhere), and no audit language (token-verified:
"audit" occurs nowhere). Accordingly: AC, AU, IA, CA, CM, IR,
MA, MP, PE, PL, PM, PS, RA, SA, SI are all **not documented**
for this set, and the build's own access/audit machinery is
house substrate, claimed against no fork.

## Named absences (token-verified in the description)

Functions a reader would expect in a category called Media that
this description does **not** state — each verified absent at
token level in the description (the check is pinned by
`test_specs.py`):

- **Recording and playback / video on demand** — "record" and
  "playback" occur nowhere; the service is live-only. The token
  "on-demand" *does* occur once — "an on-demand low latency
  video contribution network" — describing the network's
  availability, not stored-video playback; the absence is of
  the function, and the token's presence in that sense is
  recorded rather than smoothed over.
- **Transcoding / format conversion** — "transcod" occurs
  nowhere.
- **Media library / asset management / archive** — "library"
  and "archive" occur nowhere; nothing is stored.
- **Editing / production** — "edit" and "switch" occur nowhere;
  no editing, switching, or production function is described.
- **Captions / subtitles** — "caption" and "subtitle" occur
  nowhere.
- **Named streaming protocols** — "protocol" occurs nowhere;
  the description names no transport protocol at all (the
  build's route records therefore carry only an optional
  caller-stated protocol label, validated against no list).
- **Scheduling / playout** — "schedul" occurs nowhere.
- **Advertising insertion** — "advertis" occurs nowhere.
- **Viewership / usage analytics** — "analytics" and
  "viewership" occur nowhere; the monitoring claimed is status,
  not audience measurement.
- **DRM / rights management** — "drm" and "rights management"
  occur nowhere.
- **Content delivery / CDN** — "content delivery" and "cdn"
  occur nowhere; the destinations named are agency networks
  and commercial cloud destinations, reached by the fork's own
  routing.
- **Storage** — "storage" occurs nowhere, consistent with the
  live-only surface.
- **Scoring of any kind** — "score" and "scoring" occur
  nowhere; the build's no-score discipline is the
  description's own.

## Exclusions, wording artifacts, and evidence notes

- **`certified_services` is never matched** (house method:
  matching runs over `service_desc` only). For this fork the
  field is an **empty list** — no catalogue existed to exclude.
  That is recorded explicitly in
  `scratch/certified_services_notes.json` rather than assumed:
  the exclusion here is a verified absence, not a skipped step.
- **No scope-exclusion sentences exist** in the description and
  no raw hit was removed: the raw pass produced 6 hits and all
  6 stand.
- **Census citations are not automatically claims, in either
  direction:** this fork carries exactly one census citation —
  its first sentence — which verifies verbatim-exact (the raw
  substring check passes, no normalization needed) *and* is the
  evidence sentence for `live_video_transport`. Verification is
  not what makes it a claim; the taxonomy match is.
- **Four of the six families rest on sentence 3's feature
  enumeration** ("Offering start-up, integrated device control,
  stream optimization, and status & monitoring, all from a
  single browser window...") and stand at list weight — the
  weight the Human Resources set recorded for capability-list
  claims. The sentence is a genuine first-party feature list,
  not positioning prose, so the claims stand; their weight is
  recorded wherever they are cited.
- **`service_startup` records an ambiguity, not a resolution:**
  the enumeration does not say what is started — the offering,
  a stream, or a device. The family is kept because the fork
  lists the capability among its functions; the build's records
  form is the session start (the one start the transport
  surface unambiguously has), and the ambiguity itself is
  recorded here and in `scratch/ARTIFACTS.md`.
- **"All from a single browser window"** is a delivery-surface
  assertion — the console the enumerated functions are operated
  from — not a distinct function: no family was carved out of
  it, and the console itself is platform layer (a gap).
- **"Adding minimal latency"** (sentence 2) is an outcome
  assertion with no figure and no measurement method; no family
  was carved out of it, and the build computes and stores no
  latency value.

## Gaps (registered in GAPS.md at ship)

The live video transport and routing engine (the network
itself: contribution feeds, transport protocols, inter-agency
and cloud connectivity); the stream encryption implementation
(the cryptography behind the AES-256 claim); the device control
channel (actually operating field devices and encoders);
the stream optimization engine (bitrate and latency adaptation
of live streams); status and monitoring telemetry collection
(the probes and collection that produce status in operation);
and the platform layer (hosting, and the single-browser-window
management console the description names) — platform prose, as
everywhere in this repo, is the embedding organization's
substrate, not a fork function.
