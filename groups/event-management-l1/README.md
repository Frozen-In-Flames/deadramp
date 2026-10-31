# Event Management — CMMC L1 (DeadRamp Phase 2 remainder singleton)

A clean-room, open-source implementation of the records substrate
for **event and conference operations with vendor matchmaking
gatherings**: organizer and vendor registries keyed by opaque
references, event and session records with status **derived at
read**, preparation task records, outreach records, and
matchmaking rounds whose qualifying vendors are **derived at
read** from recorded participation tags — never scored. It exists
because the FedRAMP marketplace contains exactly **1 offering**
in this category at this tier, and DeadRamp builds the open
substrate underneath it.

This is a **brand-new category**: the remainder census proposed
Event Management for this fork from its own description (event
preparation, conference management, and business-matchmaking
gatherings — a function none of the 36 Phase 1 categories covers:
Collaboration covers collaborative work tools, and Marketing &
Sales does not cover event preparation or conference management).
`forks.json` files the fork "Uncategorized (none in source)"; its
source record carries an empty business-categories list. The
category here is the census proposal, not a source field —
recorded as such in the spec.

## The fork

| Fork | Tier | Status |
|---|---|---|
| **Vendor Event & Business Matchmaking Platform** — My Business Matches (FR2304546222) | FedRAMP **Low** → CMMC **L1**, SaaS, Public Cloud | FedRAMP Certified |

Full spec sheet, with every function claim carrying its source
sentence as evidence: [`specs/specs.json`](specs/specs.json).
Union contract, claim ranking, control traceability, and gaps:
[`UNION-SPEC.md`](UNION-SPEC.md).

**What the fork's own description supports: 8 claims, one per
family of an 8-family taxonomy defined from its own vocabulary** —
event preparation, conference management, vendor outreach, event
formats (onsite, hybrid, virtual), webinars, business
matchmaking, networking roundtables, and speaker engagements.
The description contains **no registration, ticketing, agenda,
fees, payment, venue, survey, recording, streaming, analytics, or
matching-algorithm vocabulary at all**: the category as this
fork's own words define it is event and conference operations
with matchmaking gatherings, and nothing else was claimed, so
nothing else is owed (full absence list in
`scratch/ARTIFACTS.md`).

## The build

The core is the records form of what those claims presuppose,
built at the FedRAMP Low/L1 baseline:

- **Organizer & vendor registries** — opaque `ref` + label only;
  the pinned record shape has no field that could hold a real
  identifier.
- **Event records** — title, a format from the claimed set
  (onsite / hybrid / virtual), and a start/end window. Status
  (`upcoming` / `live` / `concluded`) is **derived at read**,
  never stored.
- **Preparation task records** — the preparation function's
  records form: tasks on an event, completed by recorded action.
- **Session records** — the three claimed gathering kinds
  (webinar, roundtable, speaker engagement) within an event,
  windows contained by the event's window; a speaker is named by
  opaque reference only. Status derived at read.
- **Outreach records** — an organizer's outreach to a vendor
  about its own event (ownership enforced); recorded, never sent
  (delivery is Extended).
- **Matchmaking rounds & participations** — a round records the
  capability tags the organizer requires; a participation records
  the tags a vendor states for itself, only while the round is
  open, immutable, one per vendor per round.
- **Match derivation (signature invariant)** — a round's matches
  are the participations whose tag set **covers** the required
  tag set, computed on read from the participation records alone;
  **no match is ever stored**, and the result is registration
  order — never a score, rating, or ranking of any vendor.
- **Search & summary** — literal substring search; counts
  computed on read, no computed scores anywhere.
- **REST API + CLI**, role-based access (admin / member / viewer),
  and an append-only audit log recording mutations and denied
  attempts.

## Run it

```sh
PYTHONPATH=src python3 -m events serve --port 8765
# demo users: alice=admin, bob=member, carol=viewer (X-User / X-Role headers)
PYTHONPATH=src python3 -m unittest discover -s tests   # 79 tests
```

Python 3 standard library only; there is nothing to install.

## Control mapping (summary)

Built to the **FedRAMP Low / CMMC L1** baseline (NIST SP 800-53
Rev. 5 Low, cross-walked to the FAR 52.204-21 practices): access
enforcement on every operation (AC-2/AC-3), audit of mutations
and denied attempts (AU-2/AU-3, claimed on the FedRAMP Low side
only — FAR 52.204-21 has no audit practice, and AU-6/AU-9 are
Moderate selections, not claimed here), input validation at the
boundary (SI-10), and all status and matches derived from
retained records (CM-6). Full traceability table in
[`UNION-SPEC.md`](UNION-SPEC.md).

## Honesty

- **Nothing here is a FedRAMP authorization or a CMMC
  certification.** FedRAMP authorizes products; CMMC certifies
  organizations. The tier mapping is a planning equivalence. The
  fork's FedRAMP Certified status, and any property of the fork's
  own platform (including its "compliant with federal devices and
  firewalls" posture prose), belong to the fork and do **not**
  transfer to this build.
- **Matchmaking here is set coverage, not intelligence.** The
  fork's description names no matching criteria, algorithm,
  ranking, or score, so the build invents none: qualification is
  derived from tags the organizer and the vendors themselves
  recorded. A recommendation engine is a named gap, not a hidden
  feature.
- **No attendee surface exists.** The description names no
  attendee function, so there is no attendee registry and no
  record anywhere can hold a person's name, email, or phone
  number; speakers appear only as opaque references.
- **No money moves, and none is recorded.** The description
  names no fees or payments, so no record shape carries a money
  field.
- **Extended functions are specified, not implemented** (see
  UNION-SPEC gaps): the event delivery & presentation plane,
  outreach delivery transport, a matchmaking recommendation
  engine, live session facilitation, speaker sourcing & booking,
  and an identity provider. The build records outreach; it sends
  nothing. It records sessions; it presents nothing.
- **Demo identities are hooks, not an IdP.** `alice` / `bob` /
  `carol` exist so the permission matrix can be exercised; IA-2
  stays with the embedding organization.
- Claims in the spec are a **floor**: a function is claimed only
  where the offering's own marketplace description states it,
  with the sentence stored as evidence. Both census citations
  verify verbatim and both happen to be claim-bearing sentences —
  recorded as the coincidence direction; no citation was
  load-bearing. One evidence choice is corrected on the record:
  business matchmaking's evidence is sentence 5 (provision), not
  sentence 1 (the customer's need) — see `scratch/ARTIFACTS.md`.
