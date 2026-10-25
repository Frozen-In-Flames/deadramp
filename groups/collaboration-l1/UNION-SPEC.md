# Union Spec — Collaboration, CMMC L1 (DeadRamp Phase 2, Group 10)

The merged functional spec for the **Collaboration L1** sibling group:
**10 forks**, category **Collaboration**, CMMC tier **L1**. This is one
of the map's mixed-impact groups: **2 forks are FedRAMP Low** (A-SCEND;
Vyond for Government, record FR2433985791XL) and **8 are LI-SaaS**
(FedRAMP's tailored subset of the Low baseline for SaaS) — verified in
`forks.json`, and each fork's actual impact level is recorded in its
spec sheet. The member list was reconciled against `MAP.md`'s
"Collaboration — L1 (10)" section: **zero diffs** (Vyond for Government
appears twice in both, two distinct FedRAMP records for the same
product at the two impact levels).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 10
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
all 10 descriptions were present in the cached dataset.

## How functions were counted

The **same fixed 21-function taxonomy** used for the Collaboration L2
group (Group 2), byte-identical in ids, labels, and match patterns, so
counts are comparable across the category's tiers. A function is
claimed for a fork **only** when the description contains matching
text; the matching sentence is stored as the claim's evidence.

This group's descriptions are product-level marketing prose, and the
counts show it: only **6 of 10 offerings carry any tagged claim (15
claims total)**, and only 9 of the 21 functions tag at all. Four
descriptions carry none: **Overleaf** ("an online collaborative
writing and publishing tool" — plainly a collaboration product whose
wording matches none of the taxonomy's stems), **Vbrick Enterprise
Video Platform** (live and on-demand video delivery, in vocabulary
the meetings pattern does not cover), and **both Vyond for Government
records** (video creation platform; the two records share an identical
description). Their full text is in the spec sheets — nothing is
hidden, and no function was invented for them. The taxonomy was
deliberately **not** widened for this group: re-tuning match patterns
per group would corrupt cross-group comparability, which is the
map's whole point. Counts below are therefore a **floor**, and in this
group an unusually low one relative to what these products do.

## Function ranking — all 10 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | AI assistance, speech & analytics | 4 | 40% | Extended (the claims are the siblings' own AI features — Adobe's AI-branded assistants, A-SCEND's AI-powered audit tooling; this build ships no AI) |
| 2 | APIs, integrations & interoperability | 3 | 30% | **Core** (the service is API-first) |
| 3 | Access control & authentication | 2 | 20% | **Core** (L1 baseline hooks) |
| 4 | Calendaring & scheduling | 1 | 10% | **Core** (see the core-boundary note below) |
| 5 | Workflow & process automation | 1 | 10% | Extended (domain process engines that run on top of a collaboration substrate) |
| 6 | Search & discovery | 1 | 10% | **Core** (literal substring search across workspace objects) |
| 7 | Audit logging & trails | 1 | 10% | **Core** (Low-side AU tracing only — see the baseline precision note) |
| 8 | Learning, training & mentoring | 1 | 10% | Extended |
| 9 | Knowledge management & content experiences | 1 | 10% | Extended |
| 10 | Messaging & chat | 0 | 0% | **Core** (core-boundary note below) |
| 11 | Meetings, video & web conferencing | 0 | 0% | Extended (media transport — a standard-library text build carries no audio/video; the coordination surface around meetings — calendaring, channels, presence — is Core) |
| 12 | Voice, telephony & contact center | 0 | 0% | Extended (real-time media transport) |
| 13 | File sharing, storage & content management | 0 | 0% | **Core** (core-boundary note below) |
| 14 | Shared workspaces & team collaboration | 0 | 0% | **Core** (core-boundary note below) |
| 15 | Whiteboarding, visual collaboration & co-authoring | 0 | 0% | **Core** (core-boundary note below) |
| 16 | Presence & availability | 0 | 0% | **Core** (core-boundary note below) |
| 17 | Task, project & work management | 0 | 0% | Extended (board cards in Core are the seed, not a full task/project system) |
| 18 | Electronic & digital signatures | 0 | 0% | Extended (notable: Adobe Document Cloud bundles Acrobat Sign, but its description never uses the taxonomy's signature phrasing — a wording artifact, recorded rather than corrected by hand) |
| 19 | Notifications, alerts & emergency communications | 0 | 0% | **Core** (the in-platform notification queue: mentions, invites, shares) |
| 20 | Encryption | 0 | 0% | Platform note (no sibling claims it in this group; TLS support is a property of the reused service, recorded as such, not as a claim — see baseline section) |
| 21 | Records, governance & compliance management | 0 | 0% | Extended (file versioning and the audit trail in Core are the seed — notable: A-SCEND is a governance product, but its description's governance vocabulary tags only via its audit/AI claims) |

### The core-boundary note (read before judging the zeros)

Six Core functions tag **zero** claims in this group (messaging,
file sharing, workspaces, whiteboarding, presence, notifications),
and calendaring tags one. They are Core anyway, for the same reason
Group 2's spec gave for its low-count Core functions, in stronger
form: **they are the platform functions that define the Collaboration
category itself.** A merged build for this category that omitted
messaging, shared workspaces, and file sharing because ten marketing
descriptions didn't use the taxonomy's stems would not be a
collaboration build at all. The source categorizes all 10 forks as
Collaboration; their products plainly presuppose the platform
(Overleaf is real-time co-editing; Adobe Creative Cloud's own text
says "create and collaborate"; Vbrick and Vyond are shared video
platforms). The Merge Rule takes the union of what the siblings are,
not merely the union of the words their listings happen to use, and
the category's platform core was established from the full category
evidence in Group 2's spec. What this group's claims change is the
**ranking and the long tail**, not the platform: this group skews
toward content creation, documents, and learning (Adobe holds 3 of
the 10 seats; AI assistance is the top tagged family), and that skew
is preserved in the ranking above rather than averaged away.

**Differences are preserved, not averaged away**: the long tail
above (AI features, learning management, knowledge experiences,
domain workflow, e-signature) is the record of how these siblings
differ from the category's platform center. Each Extended function
names its claim family and sibling count; the per-fork spec sheets
name which siblings claim it.

## The Core — what the merged build implements (11 functions)

One coherent, standards-based collaboration service that the
category's platform presupposes, built clean-room from this spec
(implementation reused in full from Group 2 — see the reuse note in
`scratch/reuse-note.md`):

1. **Workspaces** — named shared workspaces with an owner, a member
   list, and provenance (who created it, when). Membership is the
   boundary every other core function enforces.
2. **Messaging & chat** — channels inside a workspace; messages with
   optional threading (a message may reply to another in the same
   channel); `@name` mentions of workspace members generate
   notifications.
3. **File sharing** — files shared into a workspace as versioned
   records: name, content type, size, SHA-256 digest, who shared it,
   when; re-sharing the same name creates the next version.
4. **Calendaring & scheduling** — workspace events with title, start
   and end (ISO-8601), location, and attendees; member attendees are
   notified of the invite.
5. **Presence** — a per-user availability status (`available`,
   `busy`, `dnd`, `offline`) with an optional note and an updated
   timestamp; a user sets their own presence (a platform admin may
   set anyone's).
6. **Whiteboards** — boards inside a workspace holding positioned
   text cards (text plus x/y position) that members can add and move.
7. **Search** — literal, case-insensitive substring search across a
   workspace's messages, file names, event titles, and board cards.
8. **Notifications** — a per-user queue fed by mentions, event
   invites, and file shares; entries can be listed and marked read.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced on
    every operation, layered with workspace membership (non-members
    cannot read or write a workspace's content; the platform `admin`
    role can).
11. **Audit log** — an append-only audit trail: every workspace,
    membership, channel, message, file, event, presence, board, and
    notification mutation, every search, and every denied attempt is
    recorded with actor, action, target, and UTC timestamp.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored subset of it),
  cross-walked to the FAR 52.204-21 practices that define CMMC L1.
  Derivation per the Merge Rule: union of parent baselines = Low
  (the LI-SaaS subset adds nothing beyond it), inherited in full.
  **This baseline is written fresh for this tier. Nothing of Group
  2's Moderate framing is inherited: the code is reused, the
  baseline claim is not.**
- **Feature → control family mapping (this build, at the Low
  baseline):**
  - Access control (platform roles + workspace membership) → **AC**
    (AC-2 account management, AC-3 access enforcement; FAR
    52.204-21's access-limitation practices: limit system access to
    authorized users and to the transactions and functions they are
    authorized to execute), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the service ships hooks,
    not an identity provider; FAR's practices: identify system
    users, processes, and devices, and authenticate them before
    allowing access).
  - Audit log → **AU**, **on the FedRAMP Low side of the crosswalk
    only** (AU-2 event logging, AU-3 content of audit records; the
    append-only store and permission-gated read are implementation
    properties). **Precision note:** CMMC L1 / FAR 52.204-21
    contains **no audit practice**, so no audit claim is made on
    the CMMC side, and none of Group 2's Moderate-level audit
    citations (AU-6 audit review, AU-9 protection of audit
    information) are imported here. The audit log is carried
    because the FedRAMP Low baseline carries the AU family and one
    sibling (A-SCEND, itself an audit-management platform) claims
    audit trails — not because L1 asks for it.
  - Messaging / files / events / boards / search → **SI** (SI-10
    information input validation — malformed input is rejected,
    never partially applied) and **SC** (SC-8 transmission
    confidentiality — the server runs over TLS when a certificate
    is configured; FAR's system-and-communications-protection
    practices cover boundary protection and protecting transmitted
    information at the family level). Encryption at rest is a
    deployment-layer control, stated plainly, not claimed here. No
    sibling in this group claims an encryption function (0 of 10);
    TLS support is a property of the reused service, recorded as
    such, not as a claim.
- **What this tier does not carry, and this build does not claim:**
  the Moderate/High apparatus from the sibling groups (e.g. the
  Collaboration L3 group's hash-chained audit uplift, fail-closed
  audit writes, logon lockout, auditor role, and 800-172-derived
  enhan
...[truncated 8824 chars]