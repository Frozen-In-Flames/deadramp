# Union Spec — Communication, CMMC L1 singleton (DeadRamp Phase 2, Group 37)

The functional spec for the **Communication L1 singleton**: a sibling
group of **one fork** — **Adobe Campaign** (Adobe), SaaS, Public Cloud
deployment, FedRAMP **LI-SaaS**, FedRAMP Certified (FedRAMP ID
FR1907354404). Per PIPELINE.md, singletons build after the sibling
groups with the same pipeline at group size one: this spec is the one
fork's claims under the category taxonomy, and the build is the
category substrate those claims presuppose, at this fork's own tier.

**Reconciliation (zero diffs).** `forks.json` carries exactly one
Communication / L1 entry (the fork above; its registry fields match
the raw marketplace record field for field). MAP.md omits groups of
one from its sibling-group sections by design; the reconciliation
therefore runs through the category total: MAP.md's category table
gives Communication **17** offerings, the sibling sections account
for L2 (10) + L3-adjacent (6) = 16, and 17 − 16 = **1** — this
singleton. `forks.json` confirms the same arithmetic (17 Communication
forks: 10 Moderate, 6 High, 1 LI-SaaS, none untiered).

The fork's marketplace record carries `business_categories: []`
(empty in the source); its DeadRamp category comes from the listing's
business-function filter tags, per the Phase 1 category rule. The
empty field is preserved in the spec sheet, not repaired.

## How functions were counted

The fixed **21-family taxonomy from Group 11** (Communication L2) was
applied **unchanged** — ids, labels, and matchers verified
byte-identical against Group 11's extractor — so counts are
comparable across the category's tiers. A family is claimed only when
the fork's own public description contains matching text; the first
matching sentence is stored in `specs/specs.json` as evidence.
Group 11's five wording-artifact corrections are inherited with the
taxonomy and were not re-opened. **3 claims** survive (3 raw hits, 0
removed — no new corrections were needed). Counts are a **floor**, not
a ceiling. Near-misses are itemized in `scratch/ARTIFACTS.md`; the
taxonomy was **not** re-tuned to capture them.

## Function ranking — the singleton fork under the category taxonomy

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Messaging (email & messaging channels) | **Core** — composition + delivery records |
| 1 | 1 | Reporting, dashboards & analytics | Core (records substrate); engines Extended |
| 1 | 1 | Workflow & business process automation | Extended — engines; approval-less dispatch substrate is Core |
| 4 | 0 | Email security, anti-phishing & threat protection | 0 claims in this group — absent from this singleton's union |
| 4 | 0 | AI/ML analysis & virtual assistance | 0 claims — absent ("real-time interaction management" is a near-miss, not an AI claim; see ARTIFACTS.md) |
| 4 | 0 | Notifications, alerting & critical-event communications | 0 claims — absent |
| 4 | 0 | Delivery verification, receipts & acknowledgements | 0 claims — the family's mechanics (receipts, ack tracking) are carried as substrate under Core; no claim is asserted |
| 4 | 0 | Voice, telephony, IVR & contact center | 0 claims — absent |
| 4 | 0 | Contacts, directory & constituent management | 0 claims under the verbatim pattern ("integrated customer profiles" is a recorded near-miss) — the directory is carried as presupposed substrate (boundary decision below) |
| 4 | 0 | Communications archiving, retention & records | 0 claims — absent; immutable records are Core substrate |
| 4 | 0 | Search, eDiscovery & FOIA | 0 claims — absent as a family; literal search over records is Core substrate |
| 4 | 0 | Correspondence & casework management | 0 claims — absent |
| 4 | 0 | Secure & encrypted transmission | 0 claims — the fork's "highest levels of security" assurance sentence is a recorded near-miss, not a transmission claim |
| 4 | 0 | Key & certificate lifecycle management | 0 claims — absent |
| 4 | 0 | Identity proofing, login & access control | 0 claims — RBAC is carried as Low-baseline hooks |
| 4 | 0 | Audit logging & trails | 0 claims — the audit log is carried on the FedRAMP Low side of the crosswalk only (see baseline) |
| 4 | 0 | Scheduling, events & check-in | 0 claims — send-at scheduling is carried as substrate (the fork's "right time" phrasing presupposes timed sending but does not tag) |
| 4 | 0 | Personnel/asset tracking & situational awareness | 0 claims — absent |
| 4 | 0 | Permits, passes, surveys & forms | 0 claims — absent |
| 4 | 0 | Electronic signature | 0 claims — absent |
| 4 | 0 | Payment processing | 0 claims — absent |

**The fork's excess over the substrate** (functions its description
asserts that no taxonomy family names, because the category taxonomy
was defined from the L2 group's descriptions, where no sibling is a
campaign platform): **visual campaign orchestration**, **targeted
segmentation**, **integrated customer profiles**, **cross-channel
campaign execution**, and **real-time interaction management**. These
are specified as Extended gaps below — named, not forced into
families. Named absence carried from the category record: **video
conferencing / real-time media transport is claimed by 0 forks in
this group** (and by 0 of 10 at L2); it appears in no union function.

## The Core — what the build implements (12 functions)

The same messaging substrate the category's L2 merged build
implements — the substrate this fork's claims presuppose:

1. **Directory** — contacts (`ct-`) with per-kind addresses
   (email/sms/voice/push) and groups (`grp-`) with membership; the
   recipient registry.
2. **Channels** — channel configuration records (`ch-`) by kind, with
   an enabled flag; dispatch honors the configuration.
3. **Templates** — message templates (`tpl-`) with `{placeholder}`
   rendering; a missing variable is a validation error, extras
   ignored.
4. **Message composition** — template-or-literal composition;
   recipients resolved as the order-stable, deduplicated union of
   named contacts and group members; unreachable recipients are
   recorded in `skipped_recipients`; a message with zero deliverable
   recipients is rejected whole, consuming no ids.
5. **Delivery records** — one record (`dlv-`) per recipient × channel
   kind, with a status lifecycle `queued → delivered | failed →
   acknowledged`, attempt counts, receipts, and failure reasons.
6. **Dispatch & receipts** — dispatch of due deliveries through a
   **reference transport**: a deterministic stub that marks a delivery
   `delivered` (with a receipt labelled `reference_transport: true`)
   when an enabled channel of its kind exists, else `failed` with
   `failure_reason='no_enabled_channel'`. It transmits nothing over
   any real network, and is labeled a stub in code, tests, and
   README.
7. **Scheduling** — `send_at` on composition; `dispatch_due(now)`
   picks up everything due; dispatching a not-yet-due message is a
   validation error.
8. **Acknowledgement tracking** — messages may require
   acknowledgement; `acknowledge` is valid only on a delivered
   delivery of such a message; `ack_status` reports totals and
   pending recipients.
9. **Records & search** — message and delivery records are immutable
   once written; literal case-insensitive search across contacts,
   messages, and deliveries.
10. **REST API** — the full surface over HTTP (see README endpoint
    table), with the house auth convention (X-User/X-Role against a
    demo registry; 401 unknown/mismatched, 403 permission, denied
    attempts audited).
11. **Access control (RBAC)** — admin/operator/viewer matrix enforced
    in the store before any state change or id allocation, and again
    at the service layer.
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation and every denied attempt (`<action>:denied`).

**Core-boundary decision (explicit).** Of the 12 core functions, two
are anchored in this fork's own claims — composition/delivery/dispatch
(under its `messaging` claim) and the reporting substrate (under its
`reporting_analytics` claim) — and one is anchored in part (the
approval-less dispatch substrate under `workflow_automation`, whose
engine remainder is Extended, the same disposition Group 11 gave that
family). The remaining substrate functions (directory, channels,
templates, scheduling, ack tracking, records & search, RBAC, audit)
tag **zero** claims in this group and are **carried, not claimed**:
they stand because (a) the fork's own claims presuppose them — there
is no targeted cross-channel campaign messaging without a recipient
registry, channel configuration, timed sending, and delivery records
— and (b) the category union at L2 established this substrate as the
Communication core, and a singleton inherits its category's substrate
at its own tier rather than re-deriving a lesser one. A wording
artifact is not a downgrade, and a singleton is not a lesser build.
This mirrors the recorded boundary decisions in Groups 10, 24, and
30.

**Reuse, stated explicitly.** The implementation in `src/` and the
suite in `tests/` are the shipped Group 11 (Communication L2) code,
reused — this project's own Apache-2.0 code. All 7 `src/` modules are
byte-identical to Group 11's (SHA-256 per file in
`scratch/reuse-note.md`); 13 of 15 test files are byte-identical and
the 2 differing files differ by documentation wording only (group
references in docstrings; zero test-logic changes, diff-verified).
The source carries no tier or baseline strings: the code is
tier-neutral. **What is NOT reused is the baseline claim** — Group
11's Moderate / 800-171 framing does not carry over; this group's
spec, traceability, and README are written against the Low baseline
and FAR 52.204-21 only.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this fork) on
  the crosswalk (`../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored **subset** of it for
  SaaS offerings), cross-walked to the 17 practices of **FAR
  52.204-21** that define CMMC L1. Derivation per the Merge Rule: the
  union of the Low and LI-SaaS parent baselines is the Low baseline
  itself (the subset adds nothing beyond it), inherited in full.

| Core function | Control families | How the build answers |
|---|---|---|
| Directory, groups | AC-3, AC-6, IA-2 (hooks) | Recipients are explicit records; reachability is computed from them, never assumed. FAR side: limit system access to authorized users and transactions |
| Channels | CM-6 | Channel enablement is configuration, and the dispatch gate reads it on every attempt |
| Templates, composition | SI-10 | Placeholder/variable and recipient validation before any record or id exists |
| Deliveries, dispatch, receipts | AU-2, AU-3 (Low side only), SC-8 (partial) | Every attempt is an auditable event with content; transmission protection is TLS-when-configured (see gaps) |
| Acknowledgements | AU-2 (Low side only) | Ack state is queryable per message and per recipient |
| Records & search | AU-2, AU-3 (Low side only) | Immutable records with review/search; retention/disposition engines are Extended |
| RBAC | AC-3, AC-5, AC-6, IA-2 (hooks) | Three-role matrix enforced pre-mutation at two layers. IA-2: identity is supplied by the embedding organization via user/role headers; the service ships hooks, not an identity provider |
| Audit log | AU-2, AU-3 (Low side only) | Append-only log including denied attempts; no mutation API |

**Precision notes (this tier).** (1) Audit traces to the AU family
**on the FedRAMP Low side of the crosswalk only**: FAR 52.204-21
contains no audit practice, so no audit claim is made on the CMMC
side. (2) Group 11's Moderate-level audit citations are deliberately
**not** imported here: **AU-6 and AU-9 are not Low selections** and
are not claimed; the append-only store and the admin-gated audit read
are implementation properties, stated as such. (3) The Moderate/High
apparatus from the sibling tiers (e.g. the L3 groups' hash-chained
audit, lockout machinery, 800-172-derived enhancements) is out of
scope for a Low/L1 build and is **not inherited downward**.

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source
implementation whose features trace to the Low/L1 control families.

## Implementation contract (summary)

Identical to Group 11's contract — Python 3, **standard library
only**, package `comm` under `src/`, runnable and testable with
`PYTHONPATH=src`: `errors` (`CommError`, `ValidationError`,
`NotFoundError`, `PermissionDenied`), `access` (User, role matrix),
`audit` (append-only AuditLog), `store` (CommStore: the 12 core
functions; failed operations consume no ids; permission checks
precede mutation), `service` (HTTP layer, demo registry alice=admin
/ bob=operator / carol=viewer), `__main__` (`python -m comm serve`).
`tests/`: 82 unittest tests across 13 modules, every test docstring
tracing to a core function, a claim family, or a control family; the
negative control and its live mutation verification **in this tree**
are recorded in `tests/README.md` (send-gate mutant → 4 failures;
restored SHA-256-identical, suite green).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Adobe Campaign, LI-SaaS; 3 evidenced
  claims).
- Core implemented: **12 / 12** functions above, at the Low/L1
  baseline.
- Tests: **82 run, 82 passed**, including the mutation-verified
  negative control (drill performed fresh in this tree).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions (this fork's excess over the substrate):

- **Campaign orchestration engine** — visual campaign orchestration,
  cross-channel campaign execution, campaign/journey lifecycle
  management (the fork's signature function; no taxonomy family
  names it).
- **Audience segmentation engine** — targeted segmentation over
  audience data.
- **Customer profile store & identity resolution** — integrated
  customer profiles beyond the directory's contact records.
- **Real-time interaction management** — real-time decisioning and
  interaction handling across channels.
- **Workflow / BPM engine** — campaign-creation workflow management
  as an engine, including approval chains (the claim's remainder;
  the approval-less dispatch substrate is Core).
- **Reporting / analytics engines** beyond the records, search, and
  ack-status substrate — campaign-effectiveness analytics and
  dashboards.
- **Real channel execution** — email/SMS/push delivery networks and
  direct-mail (postal) fulfillment; the core's dispatch runs through
  the labelled reference transport and transmits nothing.
- **Managed-service operations** — the fork runs as a customizable
  Managed Service; hosting and operating the platform itself is a
  platform-layer function, not part of this build.

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment);
demo identities are hooks, not an IdP — IA-2 stays with the embedding
organization.
