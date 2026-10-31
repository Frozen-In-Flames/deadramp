# Union Spec — Event Management, CMMC L1 (DeadRamp Phase 2 remainder, Event Management L1 singleton)

The singleton spec for the **Event Management** category at the
L1 tier: **1 fork**, brand-new category (the remainder census
proposed it for this fork; no group exists at any other tier) —
**Vendor Event & Business Matchmaking Platform** (My Business
Matches), FedRAMP **Low**, FedRAMP Certified, SaaS, Public Cloud.
Built under the remainder census unit
`new-singleton:Event Management|L1`.

**Membership provenance, stated plainly:** `forks.json` files this
fork "Uncategorized (none in source)" at tier L1 — its source
record carries an empty `business_categories` list. The DeadRamp
category is the **remainder census proposal**, taken from the
fork's own description: its primary function is event preparation,
conference management, and business-matchmaking gatherings, a
function none of the 36 Phase 1 categories covers (the census's
recorded reason: "Collaboration covers collaborative work tools
and Marketing & Sales does not cover event preparation or
conference management"). Reconciliation: `remainder.json` unit ==
`specs/specs.json` == {FR2304546222}, zero diff, and the fork's
own recorded fields (Low, FedRAMP Certified, L1) match the source
record exactly. MAP.md's category arithmetic is unaffected: this
fork was never in MAP.md's category counts, because MAP.md counts
the Phase 1 category field. This group's number is assigned in
the repo README at ship; this spec deliberately carries none.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **FR2304546222**.

## How functions were counted (a new category: the Group 1 method)

Event Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching
text; the first matching sentence is stored as the claim's
evidence in the spec sheet, subject to one recorded evidence
correction (below). Marketing prose gets no tags. **8 claims in
total, one per family** — the single fork claims every family its
own vocabulary defines. Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
sentence 1's "definitive source ... Event & Business Matchmaking
needs" is positioning prose stating the customer's *need*, so the
business_matchmaking claim takes its evidence from sentence 5,
the sentence that asserts provision ("let you provide ... business
matchmaking") — the extractor's one evidence exclusion; the claim
count is unchanged. Sentence 3's "compliant with federal devices
and firewalls" is compliance-posture prose and tags nothing (no
security family is carved out of posture). Sentence 4's "FedRAMP
Authorized Secure Service" is authorization-status prose; the
status is record data, not a claim. Sentence 2's trailing fragment
"in need of support" names no support function. Sentence 5's
"gathering functions" framing tags nothing; each named gathering
kind is its own family. The description carries **no hosting or
cloud language of its own**, so this taxonomy has no
hosting-platform family; "SaaS" and "Public Cloud" are
source-record fields, not claims. The fork's source record
carries `certified_services: []` — no third-party catalogue
exists to exclude — and no sentence is a scope-exclusion
sentence, so nothing was removed before matching.

**Census citation accounting:** both census citations verify as
strict verbatim substrings of the description (2/2), and both are
also claim-bearing sentences — citation 1 (sentence 2) is the
stored evidence for the four preparation/conference/outreach/
formats families, and citation 2 (sentence 5) is the stored
evidence for the four gathering families. Verification and
claiming coincide here, recorded as the coincidence direction; no
citation was load-bearing, because every claim rests on the
description itself.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Event preparation | 1 | **Core** (records) — preparation task records on the event, completed by recorded action |
| 2 | Conference management | 1 | **Core** — the event & session substrate itself (event records, session records, derived status) |
| 3 | Vendor outreach | 1 | **Core** (records) — outreach records; delivery transport is Extended |
| 4 | Event formats (onsite, hybrid, virtual) | 1 | **Core** — the format is a first-class field on every event record; the virtual delivery/presentation plane is Extended |
| 5 | Webinars | 1 | **Core** (records) — session records of the webinar kind; the webcast presentation plane is Extended |
| 6 | Business matchmaking | 1 | **Core** — matchmaking round & participation records and the match derivation; any recommendation engine is Extended |
| 7 | Networking roundtables | 1 | **Core** (records) — session records of the roundtable kind; live facilitation is Extended |
| 8 | Speaker engagements | 1 | **Core** (records) — session records of the speaker-engagement kind, speaker named by opaque reference only; speaker sourcing/booking is Extended |

**Named absences, stated plainly (token-verified; full list in
`scratch/ARTIFACTS.md`):** the description contains **no
registration, ticketing, RSVP, attendee, agenda, scheduling,
fees, payment, venue, catering, certificate, survey, recording,
streaming, email-campaign, analytics, badge, lead-retrieval, or
matching-algorithm vocabulary at all**. None of the absences is a
gap in the registry sense: nothing was claimed, so nothing is
owed. The category as this fork's own words define it is **event
and conference operations with vendor matchmaking gatherings** —
preparation, conference management, vendor outreach, three event
formats, and three gathering kinds.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *Matches are a derivation, not a score.* The
description names no matching criteria, algorithm, ranking, or
score, so the build invents none: a round records the capability
tags the organizer requires, a participation records the tags the
vendor states for itself, and the round's matches are the
participations whose tag set *covers* the required set — set
inclusion over recorded text, derived at read and never stored.
The view returns qualifying participations in registration order;
registration order is not a ranking, and no record shape carries
a score field — pinned by test. (2) *No money, because none is
described.* The fork names no fees, prices, payments, ticketing,
or sponsorship amounts, so no record shape carries a money field;
a money discipline with nothing to apply to would be decoration.
(3) *Parties are organizations; individuals are opaque
references.* Organizers and vendors are organizations known by
opaque `ref` + label. No attendee registry exists — the
description names no attendee function — and a speaker appears
only as an opaque `speaker_ref`. No record shape can hold a
person's name, email, or phone number. (4) *Records, not
delivery.* Outreach is recorded, never sent; sessions are
recorded, never presented; matches are derived, never pushed.
Every transport and presentation plane is Extended, stated here
and in the README, not left implicit.

## The Core — what the merged build implements (12 functions)

One coherent, standards-based event-operations records service
that the fork's claimed functions presuppose, built clean-room
from this spec:

1. **Organizer registry (opaque references)** — organizers
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier.
2. **Vendor registry (opaque references)** — vendor
   organizations (`ven-`) under the same pinned shape and
   discipline.
3. **Event records** — events (`evt-`) for an organizer: a title,
   a format from the claimed set (`onsite` / `hybrid` /
   `virtual`), a start/end window, and an optional location note
   (free text a caller states; never parsed). An event's status
   (`upcoming` / `live` / `concluded`) is **derived at read** from
   the window against the read clock — never stored.
4. **Preparation task records** — tasks (`prep-`) on an event:
   the records form of the claimed preparation function, created
   not-done and completed by a recorded action.
5. **Session records** — gatherings (`ses-`) within an event, of
   the three claimed kinds (`webinar`, `roundtable`,
   `speaker_engagement`), each with a window that must lie
   within its event's window; speaker-engagement sessions name
   the speaker by opaque `speaker_ref` only. Session status is
   derived at read, never stored.
6. **Outreach records** — outreach (`out-`) from an organizer to
   a vendor about one of the organizer's own events (the
   ownership is enforced), with a caller-stated channel and a
   verbatim subject. Recorded, never sent.
7. **Matchmaking round records** — rounds (`rnd-`) on an event,
   recording the capability tags the organizer requires (caller-
   stated text, normalized). A round is created `open` and closed
   by a recorded action.
8. **Participation records** — participations (`part-`) by a
   vendor in an open round, stating the capability tags the
   vendor records for itself. One per vendor per round; recorded
   only while the round is open; immutable once recorded.
9. **Match derivation (the signature invariant)** — a round's
   matches are computed on read from its participation records
   alone by the single seam `_derive_matches`: the participations
   whose tag set covers the round's required tag set, in
   participation sequence order. **No match is ever stored.** An
   empty required-tag set is satisfied by every participation
   (the empty set is a subset of every set) — stated plainly,
   not special-cased.
10. **Search & summary reporting** — literal case-insensitive
    substring search over organizers, vendors, events, and
    outreach subjects; and a summary computed on read from
    records only: registry counts, events by derived status and
    by format, sessions by kind, preparation open/done counts,
    outreach and participation counts, rounds open/closed, and a
    matches total that is a count of derived matches. Counts —
    never scores.
11. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
12. **Access control & audit log** — role-based access hooks:
    platform roles `admin`, `member`, `viewer` with a permission
    matrix enforced on every operation; and an append-only audit
    trail recording every organizer, vendor, event, preparation,
    session, outreach, round, and participation mutation, and
    every denied attempt, with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **Low** (this fork's
  impact level, recorded as-is) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline,
  cross-walked to the FAR 52.204-21 basic-safeguarding practices
  that define CMMC L1. One fork at one tier, so no merge changes
  the tier (Merge Rules 1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Organizer & vendor registries | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness is enforced in the store; identity itself is supplied by the embedding organization |
| Event records & derived status | CM-6, AU-2/AU-3 (Low side) | Events are configuration-controlled records; status is derived at read from the recorded window, reproducible from the records and the trail |
| Preparation task records | AU-2, AU-3 (Low side), SI-10 | Tasks are validated records with a recorded completion action; the lifecycle cannot be set by writing a field |
| Session records | CM-6, AU-2/AU-3 (Low side), SI-10 | Sessions are validated records; the window-within-event containment is enforced at write |
| Outreach records | AU-2, AU-3 (Low side) | Outreach is recorded with its parties and subject; the organizer/event ownership guard is enforced at write; nothing is transmitted |
| Matchmaking rounds & participations | CM-6, SI-10 | Rounds and participations are explicit, validated records; participations are accepted only while the round is open and are immutable |
| Match derivation | CM-6, AU-2/AU-3 (Low side) | Matches are derived at read from the participation records by a single seam (`_derive_matches`); nothing about them is stored, so they cannot drift from the records |
| Summary reporting & search | AU-2, AU-3 (Low side); AC-3 | Deterministic counts over the records at a stated `now`; literal search over registered records only, permission-gated |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Three-role matrix enforced before any mutation or id allocation, at the store and again at the service layer; `audit_read` is admin-only, traced to AC-3 (see precision notes) |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing
  is silently imported from other tiers' tables):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline carries
    the AU family — AU-2/AU-3 only. AU-6 (audit review) and AU-9
    (protection of audit information) are Moderate selections and
    are **not** claimed here; hash-chained audit, fail-closed
    audit writes, audit query, logon lockout, and an auditor role
    are High answers from sibling groups and are absent here by
    design.
  - **Least privilege / separation of duties:** `audit_read`
    being admin-only is a design property of this substrate,
    traced at this tier to AC-3 access enforcement; AC-5/AC-6 are
    not Low-baseline selections and are named as lineage only.
  - **Transmission:** SC-8 holds only when a certificate is
    configured (`--certfile`/`--keyfile`); the default serve mode
    is plain HTTP for local/demo use, and encryption at rest is a
    deployment-layer control, stated plainly and not claimed
    here.
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence,
  and any real compliance claim still has to be earned inside each
  regime separately.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `events` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`, `ven-`,
`evt-`, `prep-`, `ses-`, `out-`, `rnd-`, `part-`); a failed
operation consumes no id and changes nothing. Capability tags are
caller-stated strings, normalized to stripped lowercase and
deduplicated; a non-list or non-string tag raises
`ValidationError`. Any status that depends on a date (event and
session status) is derived at read and never stored; event-driven
lifecycle state (a preparation task's done flag, a round's
open/closed state) is stored, as in the sibling builds' record
lifecycles.

- `events/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read, register,
  manage, outreach, matchmake, audit_read, admin}, member =
  {read, register, manage, outreach, matchmake}, viewer =
  {read}; `require(user, action)` raises `PermissionDenied`.
- `events/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `events/store.py` — `EventsStore(audit=None)` with the
  operations named in the Core above. Role permission is enforced
  for User-like actors before any state change or id allocation;
  a plain-string actor carries identity only, and enforcement for
  those happens in the service layer (the sibling builds'
  convention). The store audits every successful mutation; the
  service layer audits denied attempts (`action:denied`) and
  audit reads, so nothing is recorded twice. The match
  derivation lives in the single seam
  `_derive_matches(participations, required_tags)`.
- `events/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User` /
  `X-Role` headers (role must match the registry). Endpoints per
  the group README. Errors are JSON `{error}` with 400/401/403/404
  as applicable. Denied attempts are audited.
- `events/__main__.py` — `python -m events serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's).
- `events/errors.py` — `EventsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**:
a mutant seam whose `_derive_matches` reverses the inclusion (a
participation qualifies when its tags are a *subset* of the
required tags) — if the suite passed against it, the match tests
would be testing that code ran, not that coverage is the rule —
plus the external mutation drill (the same patch applied to the
real `store.py`); see `tests/README.md` for the counts and the
drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Event delivery & presentation plane (the webinar webcast
  itself, virtual/hybrid session delivery, the attendee join
  experience; the build records sessions, it presents nothing)
- Outreach delivery transport (email / portal / messaging
  delivery of the recorded outreach)
- Matchmaking recommendation & pairing-suggestion engine
  (proactive pairing beyond the recorded-criteria coverage
  derivation; the build derives qualification from recorded tags
  and suggests nothing)
- Live session facilitation (roundtable moderation tooling,
  webinar interaction — chat, polling, Q&A; "interactive" in the
  fork's prose is an adjective over the gathering kinds, and its
  tooling is this gap)
- Speaker sourcing & booking (finding, contracting, and
  scheduling speakers beyond the opaque reference a session
  record carries)
- Identity provider / identity management service (IA-2 stays
  with the embedding organization)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **8 tagged claims** (one per
  taxonomy family, each with its source sentence as evidence).
- Core: **12 / 12** core functions implemented, at the Low/L1
  baseline, each with tracing tests.
- Tests: see `tests/README.md` for the count (filled in from the
  build, not stated here), including the mutation-verified
  match-derivation negative control.
- Extended: the 6 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
