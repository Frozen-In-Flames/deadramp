# Media — untiered (DeadRamp Phase 2, Untiered Set 27)

An **untiered set** of DeadRamp: a fork whose FedRAMP impact
level is "Unknown" in the marketplace source. It carries no
FedRAMP baseline, so there is nothing to crosswalk: its tier
stays `null`, no CMMC equivalence is drawn, and the merged build
is built to the fork's **documented control claims** only — the
control language its own description actually uses, traced in
UNION-SPEC.md, never filled in from a baseline.

Media is also a **new category** for this repo: no tiered group
exists at any level, so there was no founding taxonomy to
inherit and no substrate to carry. The taxonomy below was
defined fresh from this fork's own description (the
new-category method used for Contract Management and Storage),
and the core was built fresh in the house architecture. If
tiered Media forks ever appear, this set's taxonomy becomes the
category's taxonomy, tested against their prose the way every
founding taxonomy here has been.

## The fork (1)

| Fork | Vendor | Product | Status | Claims |
|------|--------|---------|--------|-------:|
| FR2218359666 | Haivision Systems, Inc. | Haivision Hub for Government (HUB-GOV) | FedRAMP In Process | 6 |

Spec sheet: `specs/specs.json`. Union analysis: `UNION-SPEC.md`.

**Haivision Hub for Government** is a live video transport
service: it routes live streaming video between agency networks
and commercial cloud destinations with AES-256 encryption of
the streams, and offers start-up, integrated device control,
stream optimization, and status & monitoring from a single
browser window — filed Uncategorized in the source, assigned to
Media by the census from its description ("Live video streaming
transport service"). Its description is three sentences and
entirely live: nothing in it records, stores, plays back, or
edits video.

## Taxonomy (6 families, defined from this description)

`live_video_transport`, `stream_encryption`, `service_startup`,
`device_control`, `stream_optimization`, `status_monitoring`.
Each family's patterns are drawn from the description's own
phrases; the derivation is stated in full in UNION-SPEC.md.
Because the taxonomy comes from exactly one description, every
count here is a floor over this set only. Six claims, one per
family; four of the six rest on the third sentence's feature
enumeration and stand at list weight.

## The merged build — `media`

A fresh core: Python standard library only, in `src/media/`
(errors, access, audit, store, service, CLI). Eleven numbered
functions in UNION-SPEC.md: organization registry; endpoint
records (agency networks and cloud destinations); route records
with **state derived at read, never stored**; stream session
records behind the **one-live-session guard** — a second start
on a route with a live session is refused, records nothing, and
consumes no id, the build's signature invariant; device records;
control-action records (**records only — nothing is sent to any
device**); optimization profile records (settings stored
verbatim, never executed); status snapshot records; derived
current-status and network-status views; search and a
count-only summary; a REST API; and access/audit hooks.

The build holds records about media, never media: no record
shape can hold video, a stream payload, or a file. It transports
nothing, records nothing, plays nothing back, and transcodes
nothing. It performs **no cryptography** — a route's encryption
label is caller-stated metadata, and the fork's AES-256 claim is
its own. It computes no score and no latency figure (the
description's "minimal latency" is the fork's prose), and it
holds **no money shape at all**, because the description states
no fee, price, or budget. Endpoints and devices are opaque
references; no record can hold a device address or credential.

## Running

Server (demo users alice/bob/carol via `X-User` / `X-Role`
headers):

    PYTHONPATH=src python3 -m media serve --port 8765

Tests (67):

    PYTHONPATH=src python3 -m unittest discover -s tests

Demo users: alice (admin), bob (operator), carol (viewer). Demo
identities are hooks, not an IdP — authentication stays with the
embedding organization.

## Documented control claims

With no tier, there is no baseline section: UNION-SPEC.md
carries a **Documented control claims** section instead. Its
whole substance is one family — SC, documented at family weight
from the fork's own sentence asserting "AES-256 encryption of
live streams", a named mechanism, traced as the fork's claim —
plus the bounds recorded beside it: "securely" is an adverb and
documents nothing; device control is a product function, not
access control; status & monitoring is the product's function,
not posture language. Every other 800-53 family is listed
**not documented**: the description contains no access-control,
identity/authentication, or audit language (token-verified).
The build's own access and audit machinery is house substrate,
claimed against no fork. A fork's documented control language
is its claim, never this build's attainment.

## Honesty

- **Tier is null.** The fork is "Unknown" in the source; nothing
  here assigns a tier, draws a CMMC equivalence, or asserts a
  baseline, and tests pin `cmmc_tier: null` on the sheet.
- **New category.** The taxonomy is this set's own, derived from
  one three-sentence description; the counts are a floor over
  this set only.
- **Every claim traces** to the fork's own description sentence,
  stored as evidence on its sheet. Matching ran over the
  description only: the fork's `certified_services` field is an
  **empty list** — no catalogue existed to exclude, recorded
  explicitly rather than assumed.
- **Weights are stated, not smoothed:** four claims ride one
  feature-enumeration sentence at list weight, and
  `service_startup` keeps an ambiguity the fork's prose leaves
  open (what is started is unstated) — recorded in UNION-SPEC.md
  rather than resolved.
- **Census citations are not automatically claims** (in either
  direction): this fork's single citation verifies
  verbatim-exact and happens to be the transport claim's
  evidence sentence; verification is not what makes it a claim.
- **Extended functions, by name:** the live video transport and
  routing engine (the network itself); the stream encryption
  implementation; the device control channel; the stream
  optimization engine; status and monitoring telemetry
  collection; and the platform layer (hosting, and the
  single-browser-window console the description names), which
  is substrate, not a fork function.
- **Named absences** (token-verified in the description): no
  recording, no playback or video on demand ("on-demand" occurs
  once, describing the network's availability), no transcoding,
  no media library or archive, no editing or switching, no
  captions, no named streaming protocol, no scheduling, no
  advertising, no viewership analytics, no DRM, no content
  delivery network, no storage, no scoring. The description is
  a live-transport surface entire.
