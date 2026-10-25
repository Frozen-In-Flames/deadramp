# Union Spec — Communication, CMMC L2 (DeadRamp Phase 2, Group 11)

The merged functional spec for the Communication sibling group at the L2
tier: **10 forks, all FedRAMP Moderate**, reconciled zero-diff three ways
(`specs/specs.json` ↔ `forks.json` ↔ MAP.md "Communication — L2 (10)").

The group: Abnormal AI for Government (Abnormal AI) · Archive360 Platform
(Archive360 platform) · Omega Platform (BlackOhm) · Critical Event
Management Suite (Everbridge) · Keyfactor for Government (Keyfactor) ·
IQ FedCloud (Leidos Digital Solutions, Inc.) · Maximus Intelligent Virtual
Assistant (MIVA) (MAXIMUS Inc.) · RecAccess (RecAccess) · GetEKKO
(Red Rock Group Holdings) · Trellix Email Security GovCloud (Trellix).

This is a heterogeneous group. The source's "Communication" category
collects email-security engines, a communications archiving platform, a
mass-notification service, a certificate lifecycle manager, an IVR virtual
assistant, a correspondence/casework CRM, a personnel tracker, a recreation
permits system, and a secure-messaging relay. There is no single product
they all are. What they share, and what the claim counts below prove, is a
**substrate**: recipients held in a directory, messages composed and
recorded, delivery attempted per recipient over configured channels, with
status, receipts, acknowledgements, scheduling, access control, and an
audit trail. The merged build implements that substrate; each vendor's
domain engine on top of it is an Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General Services
Administration, last change 2026-10-22) was sentence-split and matched
against a 21-family taxonomy defined from this category's descriptions.
A family is claimed only when the offering's own description contains
matching text; the first matching sentence is stored in
`specs/specs.json` as evidence, so every claim is auditable. 52 claims
survived. Five wording-artifact corrections were needed and are documented
in `scratch/ARTIFACTS.md` (57 raw hits → 52): "signature-less" falsely
tagging e-signature (Trellix), an attacker's "delivery mechanism" falsely
tagging delivery verification (Trellix), "user-reporting phishing" falsely
tagging reporting (Abnormal), "suspense tracking" falsely tagging
personnel tracking (IQ FedCloud), and disaster "business events" falsely
tagging scheduling (Everbridge). **No fork has zero claims** — the floor
is a true floor, not an artifact of missing text. Per-fork claim counts:
IQ FedCloud 9, Archive360 Platform 8, RecAccess 7, Omega Platform 5,
Trellix Email Security GovCloud 5, Abnormal AI for Government 4,
Keyfactor for Government 4, GetEKKO 4, Critical Event Management Suite 3,
MIVA 3.

## Function ranking — all 10 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 8 | Messaging (email & messaging channels) | **Core** — composition + delivery records |
| 2 | 5 | Reporting, dashboards & analytics | Core (records/ack-status substrate); engines Extended |
| 3 | 4 | Notifications, alerting & critical-event communications | **Core** — templates, dispatch, scheduling |
| 3 | 4 | Identity proofing, login & access control | **Core** — RBAC; identity products Extended |
| 5 | 3 | Delivery verification, receipts & acknowledgements | **Core** — receipts + ack tracking |
| 5 | 3 | Workflow & business process automation | Extended — engines; approval-less dispatch substrate is Core |
| 5 | 3 | Scheduling, events & check-in | **Core** — send-at scheduling |
| 8 | 2 | Email security, anti-phishing & threat protection | Extended — detection engines |
| 8 | 2 | AI/ML analysis & virtual assistance | Extended — models |
| 8 | 2 | Communications archiving, retention & records | Extended — archiving engines; immutable records are Core |
| 8 | 2 | Search, eDiscovery & FOIA | Core — search over records; eDiscovery production Extended |
| 8 | 2 | Correspondence & casework management | Extended — casework depth |
| 8 | 2 | Secure & encrypted transmission | Extended — E2E transport; channel config is Core |
| 8 | 2 | Key & certificate lifecycle management | Extended — CA automation |
| 8 | 2 | Audit logging & trails | **Core** — append-only audit log |
| 16 | 1 | Voice, telephony, IVR & contact center | Extended — media + conversation engines |
| 16 | 1 | Contacts, directory & constituent management | **Core** — directory |
| 16 | 1 | Personnel/asset tracking & situational awareness | Extended — device/location platform |
| 16 | 1 | Permits, passes, surveys & forms | Extended — domain system |
| 16 | 1 | Electronic signature | Extended — signature execution |
| 16 | 1 | Payment processing | Extended — payment rails |

Named absences: **video conferencing / real-time media transport is
claimed by 0 siblings in their descriptions** and appears in no union
function; it is recorded here so the absence is a finding, not an
oversight. Multi-tenancy is claimed in prose by several siblings
(Abnormal, Keyfactor, IQ FedCloud, GetEKKO) but is a deployment property,
not a function; the build is a single-tenant reference deployment and
says so (see gaps).

## The Core — what the merged build implements (12 functions)

1. **Directory** — contacts (`ct-`) with per-kind addresses
   (email/sms/voice/push) and groups (`grp-`) with membership; the
   recipient registry every sibling presupposes.
2. **Channels** — channel configuration records (`ch-`) by kind, with an
   enabled flag; dispatch honors the configuration.
3. **Templates** — message templates (`tpl-`) with `{placeholder}`
   rendering; a missing variable is a validation error, extras ignored.
4. **Message composition** — template-or-literal composition; recipients
   resolved as the order-stable, deduplicated union of named contacts
   and group members; unreachable recipients are recorded in
   `skipped_recipients`; a message with zero deliverable recipients is
   rejected whole, consuming no ids.
5. **Delivery records** — one record (`dlv-`) per recipient × channel
   kind, with a status lifecycle `queued → delivered | failed →
   acknowledged`, attempt counts, receipts, and failure reasons.
6. **Dispatch & receipts** — dispatch of due deliveries through a
   **reference transport**: a deterministic stub that marks a delivery
   `delivered` (with a receipt labelled `reference_transport: true`)
   when an enabled channel of its kind exists, else `failed` with
   `failure_reason='no_enabled_channel'`. It transmits nothing over any
   real network, and is labeled a stub in code, tests, and README.
7. **Scheduling** — `send_at` on composition; `dispatch_due(now)` picks
   up everything due; dispatching a not-yet-due message is a validation
   error.
8. **Acknowledgement tracking** — messages may require acknowledgement;
   `acknowledge` is valid only on a delivered delivery of such a
   message; `ack_status` reports totals and pending recipients (the
   Everbridge "deliver and verify" and Omega/RecAccess acknowledgement
   pattern, as substrate).
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

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is the
tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110 practices
of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`. No parent
carried a higher or lower baseline, so the merge changes no tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Directory, groups | AC-3, AC-6, IA-2 (hooks) | Recipients are explicit records; reachability is computed from them, never assumed |
| Channels | CM-6, SA-4 | Channel enablement is configuration, and the dispatch gate reads it on every attempt |
| Templates, composition | SI-10 | Placeholder/variable and recipient validation before any record or id exists |
| Deliveries, dispatch, receipts | AU-2, AU-3, SC-8 (partial) | Every attempt is an auditable event with content; transmission protection is TLS-when-configured (see gaps) |
| Acknowledgements | AU-2, AU-6 | Ack state is queryable per message and per recipient |
| Records & search | AU-6, SI-12 (partial) | Immutable records with review/search; retention/disposition engines are Extended |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization and
confers no CMMC certification; it is an open-source implementation whose
features trace to the Moderate/L2 control families.

## Implementation contract (summary)

`src/comm/` (Python stdlib only): `errors` (`CommError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, role matrix), `audit` (append-only AuditLog), `store`
(CommStore: the 12 core functions; failed operations consume no ids;
permission checks precede mutation), `service` (HTTP layer, demo
registry alice=admin / bob=operator / carol=viewer), `__main__`
(`python -m comm serve`). `tests/`: 82 unittest tests across 13 modules,
every test docstring tracing to a core function, a sibling claim, or a
control family; the negative control and its live mutation verification
are recorded in `tests/README.md` (send-gate mutant → 4 failures;
restored SHA-256-identical, suite green).

## Coverage statement (for this build)

- Forks spec'd: **10 / 10**, each with evidenced claims (52 total).
- Core implemented: **12 / 12** functions above.
- Tests: **82 run, 82 passed**, including the mutation-verified
  negative control.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Email security & threat-detection engines (Abnormal AI, Trellix):
  behavioral baselining, detonation, quarantine, remediation.
- AI/ML models and virtual-assistant intelligence, including MIVA's
  conversational IVR and Abnormal's autonomous triage.
- Voice/telephony media, IVR conversation engines, and carrier
  integration; video/media transport (0 claims in this group).
- Archiving & eDiscovery engines (Archive360): multi-channel capture at
  scale, retention/disposition, legal holds, FOIA production.
- Correspondence/casework depth (IQ FedCloud): FOIA casework, grants,
  inter-agency (IQ2IQ) exchange, suspense workflows.
- Key & certificate lifecycle automation (Keyfactor): CA connectors,
  issuance, deployment, expiry prevention workflows.
- End-to-end encrypted message transport (GetEKKO's payload-blind
  relay) and identity proofing.
- Personnel/asset tracking platform (Omega): devices, live location,
  geofencing, after-action analytics.
- Permits/passes/surveys and payment processing (RecAccess domain,
  incl. Pay.gov); e-signature execution.
- Workflow/BPM engines and reporting/analytics engines beyond the
  records, search, and ack-status substrate.

Platform layer (gap-listed, never implied closed): encryption at rest
(deployment layer); TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment);
demo identities are hooks, not an IdP — IA-2 stays with the embedding
organization.
