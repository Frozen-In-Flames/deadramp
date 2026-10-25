# Union Spec — Communication, CMMC L3-adjacent (DeadRamp Phase 2, Group 14)

The merged functional spec for the **Communication L3-adjacent**
sibling group: **6 forks**, category **Communication**, CMMC tier
**L3-adjacent** (every member is FedRAMP **High** in `forks.json` —
verified, so the group is single-tier and the merge takes the group
baseline in full, per Merge Rule 2). The member list in `forks.json`
was reconciled against `MAP.md`'s "Communication — L3-adjacent (6)"
section: **zero diffs** in both directions.

The group: Akamai Cloud (Akamai) · Artera Harmony Federal Edition
(Artera) · Enterprise Cloud Fax Government (ECFax) (Consensus Cloud
Solutions) · ETHERFAX GovCloud (ETHERFAX) · Hypori Government Cloud
(Hypori, Inc.) · Motorola Solutions Federal Cloud (MSFC) (Motorola
Solutions).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 6
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
all 6 descriptions were present in the cached dataset.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 11 merged build** (`../communication-l2/`) — itself
   the union of the 10 Communication L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room communications substrate service.
2. This group's **6 High forks**, via the spec sheets in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheets are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was re-run
independently by the coordinator, and both negative controls were
mutation-verified by patching the implementation (see Verification
below).

**Reuse, stated explicitly:** where functions overlap, this build
reuses Group 11's own open-source code (Apache-2.0, ours). The
package keeps Group 11's seven-module layout (`errors`, `access`,
`audit`, `store`, `service`, `__main__`, `__init__` — the last
byte-identical); six modules were modified for the tier uplift
(`errors.py`, `access.py`, `audit.py`, `store.py`, `service.py`,
`__main__.py`). The uplift analysis below names what the High
baseline demanded beyond the L2 core and what was done about each
item — implemented, or gap-listed by name.

## How functions were counted

The same fixed 21-family taxonomy as Group 11 (verbatim — same ids,
labels, and matching patterns, including its five documented
wording-artifact corrections) was matched against each offering's
own public description. A function is claimed for a fork **only**
when the description contains matching text; the matching sentence
is stored as the claim's evidence in the spec sheet. 5 of 6
offerings carry at least one tagged claim (**11 claims** in total);
one description carries none: **Akamai Cloud**'s listing is
1,543 characters of platform and accreditation prose (delivery
fabric, DoD IL5 direction, named edge/security services) with no
taxonomy vocabulary. Its full text is still in the spec sheet —
nothing is hidden, and no function was invented for it. No new
wording-artifact corrections were needed for this group: every one
of the 11 matched sentences asserts a customer-facing function of
its offering. Counts below are therefore a **floor**, not a ceiling,
on what these products do.

The floor effect is stronger at High than it was at Moderate, and
the spec says so plainly: High listings are written as boundary
and enclave descriptions. The group's richest sheet is Hypori
Government Cloud (3 claims) — a virtual-workspace enclave described
by its TLS tunnel, its certificate handling, and its Zero Trust
posture. The two fax/data-exchange platforms (ECFax, ETHERFAX
GovCloud) describe transmission security and hosting assurance, not
features. Nobody familiar with these products believes the group
lacks directories, delivery records, or audit trails; the listings
simply do not enumerate them. The ranking below is read with that
lens.

## Function ranking — all 6 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 2 | Identity proofing, login & access control | **Core** — RBAC, uplifted (AC-7 lockout, auditor role — see below); identity products Extended |
| 1 | 2 | Workflow & business process automation | Extended — engines; approval-less dispatch substrate is Core |
| 1 | 2 | Secure & encrypted transmission | Extended — E2E transport; channel configuration is Core |
| 4 | 1 | Messaging (email & messaging channels) | **Core** — composition + delivery records |
| 4 | 1 | Reporting, dashboards & analytics | Core (records/ack-status substrate); engines Extended |
| 4 | 1 | Notifications, alerting & critical-event communications | **Core** — templates, dispatch, scheduling |
| 4 | 1 | Key & certificate lifecycle management | Extended — CA automation |
| 4 | 1 | Voice, telephony, IVR & contact center | Extended — media + conversation engines |
| 9 | 0 | Delivery verification, receipts & acknowledgements | **Core** — receipts + ack tracking (see the core-boundary note) |
| 9 | 0 | Scheduling, events & check-in | **Core** — send-at scheduling (see the core-boundary note) |
| 9 | 0 | Contacts, directory & constituent management | **Core** — directory (see the core-boundary note) |
| 9 | 0 | Audit logging & trails | **Core** — append-only, hash-chained audit (see the core-boundary note) |
| 9 | 0 | Search, eDiscovery & FOIA | Core — search over records; eDiscovery production Extended |
| 9 | 0 | Email security, anti-phishing & threat protection | Extended — detection engines |
| 9 | 0 | AI/ML analysis & virtual assistance | Extended — models (Artera's virtual agents are this family's substance at High, described without the taxonomy's vocabulary) |
| 9 | 0 | Communications archiving, retention & records | Extended — archiving engines; immutable records are Core |
| 9 | 0 | Correspondence & casework management | Extended — casework depth |
| 9 | 0 | Personnel/asset tracking & situational awareness | Extended — device/location platform |
| 9 | 0 | Permits, passes, surveys & forms | Extended — domain system |
| 9 | 0 | Electronic signature | Extended — signature execution |
| 9 | 0 | Payment processing | Extended — payment rails |

Named absences, preserved from Group 11's spec and still true here:
**video conferencing / real-time media transport is claimed by 0
siblings** in either tier's descriptions and appears in no union
function; it is recorded so the absence is a finding, not an
oversight. Multi-tenancy is a deployment property, not a function;
the build is a single-tenant reference deployment and says so (see
gaps).

**Core-boundary note (the wording-artifact decision, stated once
and plainly):** delivery verification, scheduling, contacts &
directory, and audit logging tag **zero** claims in this group, and
messaging tags one — yet all remain Core. The core is not
re-derived per tier. Under the Merge Rule, the L2 union is carried
upward whole (Rules 1–2); dropping a substrate function at the
higher tier because High listings are boundary prose would be a
downgrade caused by a description-wording artifact, and Group 11
already established these functions as the substrate every sibling
presupposes (recipients in a directory, messages composed and
recorded, delivery attempted per recipient with receipts and
acknowledgements, an audit trail). What changes at High is the
descriptions' vocabulary, not the substrate. This is the same
decision Group 6 recorded for Collaboration at High.

**How this group differs from Group 11 (L2)** — preserved, not
averaged away: at High, "communication" predominantly means a
*governed transmission enclave*: two fax/data-exchange platforms
(ECFax, ETHERFAX), a virtual-workspace enclave (Hypori), a patient
communications suite (Artera), a mission-critical communications
cloud (Motorola MSFC), and a cloud delivery platform (Akamai).
Claim mass shifts to platform-level families — identity & access
(2 of 6), workflow automation (2 of 6), secure transmission
(2 of 6) — while the feature-enumerating substrate families
collapse (messaging 1 of 6 vs 8 of 10 at L2; delivery verification,
scheduling, directory, audit all 0). The long tail (fax transport
networks, virtual-agent conversation engines, virtual-workspace
streaming, mission-critical voice ecosystems, edge delivery) is the
record of how the siblings differ; the per-fork spec sheets name
which siblings claim each function.

## The Core — what the merged build implements (12 functions, at the High baseline)

The same 12 substrate functions as Group 11, carried up to the High
baseline:

1. **Directory** — contacts (`ct-`) with per-kind addresses
   (email/sms/voice/push) and groups (`grp-`) with membership; the
   recipient registry every sibling presupposes.
2. **Channels** — channel configuration records (`ch-`) by kind,
   with an enabled flag; dispatch honors the configuration.
3. **Templates** — message templates (`tpl-`) with `{placeholder}`
   rendering; a missing variable is a validation error, extras
   ignored.
4. **Message composition** — template-or-literal composition;
   recipients resolved as the order-stable, deduplicated union of
   named contacts and group members; unreachable recipients are
   recorded in `skipped_recipients`; a message with zero deliverable
   recipients is rejected whole, consuming no ids.
5. **Delivery records** — one record (`dlv-`) per recipient ×
   channel kind, with a status lifecycle `queued → delivered |
   failed → acknowledged`, attempt counts, receipts, and failure
   reasons.
6. **Dispatch & receipts** — dispatch of due deliveries through a
   **reference transport**: a deterministic stub that marks a
   delivery `delivered` (with a receipt labelled
   `reference_transport: true`) when an enabled channel of its kind
   exists, else `failed` with `failure_reason='no_enabled_channel'`.
   It transmits nothing over any real network, and is labeled a stub
   in code, tests, and README.
7. **Scheduling** — `send_at` on composition; `dispatch_due(now)`
   picks up everything due; dispatching a not-yet-due message is a
   validation error.
8. **Acknowledgement tracking** — messages may require
   acknowledgement; `acknowledge` is valid only on a delivered
   delivery of such a message; `ack_status` reports totals and
   pending recipients.
9. **Records & search** — message and delivery records are
   immutable once written; literal case-insensitive search across
   contacts, messages, and deliveries.
10. **REST API** — the full surface over HTTP (see README endpoint
    table), with the house auth convention (X-User/X-Role against a
    demo registry; 401 unknown/mismatched, 403 permission, denied
    attempts audited), plus the High-baseline audit endpoints
    (`/audit` filters, `/audit/verify`).
11. **Access control (RBAC)** — admin/operator/viewer matrix
    enforced in the store before any state change or id allocation,
    and again at the service layer, plus the **`auditor`** role
    (audit review only) and unsuccessful-logon lockout (uplifts,
    below).
12. **Audit log** — append-only, **hash-chained, tamper-evident**
    audit trail with audit search/reduction, chain verification,
    and fail-closed write behavior (uplifts, below), recording every
    mutation and every denied attempt (`<action>:denied`).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. All 6 parent forks sit at High, and the
  cross-tier parent (Group 11's build) sat at Moderate; the union
  baseline is therefore the High baseline, un-diluted (Merge
  Rule 1), inherited in full (Merge Rule 2). "Adjacent" remains
  deliberate wording, as in the crosswalk: L3 is not identical to
  FedRAMP High; it is the same assurance weight class.
- **Feature → control family mapping (carried from Group 11):**
  - Directory, groups → **AC-3, AC-6, IA-2 (hooks)** (recipients are
    explicit records; reachability is computed from them, never
    assumed).
  - Channels → **CM-6, SA-4** (channel enablement is configuration,
    and the dispatch gate reads it on every attempt).
  - Templates, composition → **SI-10** (placeholder/variable and
    recipient validation before any record or id exists).
  - Deliveries, dispatch, receipts → **AU-2, AU-3, SC-8 (partial)**
    (every attempt is an auditable event with content; transmission
    protection is TLS-when-configured — see gaps).
  - Acknowledgements → **AU-2, AU-6** (ack state is queryable per
    message and per recipient).
  - Records & search → **AU-6, SI-12 (partial)** (immutable records
    with review/search; retention/disposition engines are Extended).
  - RBAC → **AC-3, AC-5, AC-6, IA-5 (hooks)** (role matrix enforced
    pre-mutation at two layers; AC-5 uplifted — see below).
  - Audit log → **AU-2, AU-3, AU-9** (append-only log including
    denied attempts; uplifted — see below).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3; 800-172 audit requirements) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently; the service layer swallowed all audit errors | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store records the audit entry *before* committing a mutation (audit-before-commit), so an operation whose audit write fails proceeds not at all — no object, no id consumed; the service propagates the error as HTTP 500 `{"error": "audit write failed"}` and never returns a stack trace |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter; an expired lock clears itself |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 11, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here — even though one sibling (ETHERFAX) describes its own hosting in FIPS-140-3 terms; that is the sibling's platform claim, not this build's |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build; retention rides with the Extended archiving & records function |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `comm` under `src/`,
runnable and testable with `PYTHONPATH=src`. The contract is Group
11's, unchanged except for the uplift deltas marked **[L3]**. Ids
are sequential per object type with fixed prefixes (`ct-`, `grp-`,
`ch-`, `tpl-`, `msg-`, `dlv-`); a failed operation consumes no id
and changes nothing. All timestamps are UTC ISO-8601.

- `comm/errors.py` — `CommError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (as Group 11), plus **[L3]**
  `AuditWriteError`: raised when an audit write fails; the
  operation being audited fails closed.
- `comm/access.py` — `User(name, role)`; roles
  `admin|operator|viewer|auditor` **[L3]**; actions `contact_read,
  channel_read, template_read, records_read, contact_write,
  group_write, template_write, message_compose, dispatch,
  ack_record, channel_write, audit_read`. `PERMISSIONS`: admin ⊇ all
  twelve; operator = the four reads + {contact_write, group_write,
  template_write, message_compose, dispatch, ack_record}; viewer =
  the four reads; **auditor = {audit_read}** **[L3]**;
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`. Plain-string actors carry
  identity but no role (Group 11 convention, unchanged).
- `comm/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry dict with keys `ts, actor, action,
  target, details` plus **[L3]** `seq, prev_hash, hash` (SHA-256 of
  the canonical JSON of `{seq, ts, actor, action, target, details,
  prev_hash}`); raises **[L3]** `AuditWriteError` and rolls back
  the in-memory append if the JSONL write fails. `.entries()`
  returns all entries. **[L3]** `.query(actor=None, action=None,
  target=None, since=None, until=None)` returns filtered entries
  (since/until are ISO strings compared against `ts`, inclusive);
  `.verify_chain()` returns `(ok, first_bad_index_or_None)`.
  Append-only; optional JSONL file; loaded entries participate in
  chain verification.
- `comm/store.py` — `CommStore(audit=None)`, Group 11's methods,
  shapes, and audit action names unchanged, with one **[L3]**
  structural delta: the store records the audit entry **before**
  committing each mutation (audit-before-commit, AU-5), peeking the
  next id for the audit record without consuming it. If the audit
  write raises `AuditWriteError`, it propagates and the store is
  completely unchanged — no object stored, no delivery created, no
  counter consumed, no field flipped. (Group 11 recorded after
  mutating; the visible success-path behavior — entries, ordering,
  return values — is identical.)
- `comm/service.py` — `make_server(host, port, store, audit, users,
  max_failures=3, lockout_seconds=300)` **[L3 kwargs]** →
  `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth
  via `X-User` / `X-Role` headers (the role must match the
  registry; unknown user or mismatched role → 401). **[L3]**
  consecutive auth failures are tracked per username; at
  `max_failures` the username locks for `lockout_seconds` (403,
  audited `auth:locked`); success resets; an expired lock clears
  itself. Endpoints as Group 11 (`GET /health`, contacts / groups /
  channels / templates / messages / deliveries / dispatch-due /
  search / audit), plus **[L3]** `GET /audit/verify` → `{ok,
  entries, first_bad_index}` (audit_read; `entries` counts the
  trail before this read's own `audit_read` entry is recorded) and
  `GET /audit` filter parameters `actor, action, target, since,
  until`. Denied attempts (401 and 403) are audited with the action
  name suffixed `:denied`; **[L3]** an `AuditWriteError` anywhere
  in the request path surfaces as HTTP 500 `{"error": "audit write
  failed"}`; no stack trace is ever returned.
- `comm/__main__.py` — `python -m comm serve --host --port
  [--audit-log PATH] [--certfile --keyfile] [--max-failed-logins N]
  [--lockout-seconds S]` **[L3 flags]** with demo users
  `alice=admin, bob=operator, carol=viewer, dana=auditor` **[L3]**
  (documented as demo identities; production identity is the
  embedding organization's, per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to. 138 tests: the Group 11 suite inherited and adapted (93 tests
across the 13 inherited files — the original 82 plus 11 added
inside those files by the adaptations, listed in
`tests/README.md`) plus 45 new tests in 6 files covering the hash
chain, fail-closed audit behavior, audit query, logon lockout, the
auditor role, and the `/audit/verify` endpoint. Two **negative
controls**:

1. The send-gate mutant (carried from Group 11): a store subclass
   whose channel lookup always returns a fake enabled channel; the
   canonical expectation is shown to reject it — a delivery on a
   disabled or absent channel must end `failed` with
   `failure_reason='no_enabled_channel'`, and the mutant is
   demonstrated to deliver anyway — proving the suite catches that
   defect class rather than merely passing.
2. **[L3]** Audit tamper: mutating a stored audit entry in place
   makes `verify_chain()` report failure at exactly that entry's
   index, and a naive always-`(True, None)` verifier is shown to
   accept the tampered log — proving the chain catches the
   tampering defect class rather than merely existing.

**Verification (mutation drills, recorded in `tests/README.md`):**
patching the real send-gate condition in `src/comm/store.py`
(`if channel is None:` in `CommStore._dispatch_deliveries`) to
`if False:` made the suite fail (**138 ran, 4 failed** — the two
dispatch channel-gate tests and the two negative-control canonical
cases, the same four as Group 11's drill); the file was restored
SHA-256-identical (`bfc7877c…`) and the suite returned to green.
Separately, patching `_entry_hash` in `src/comm/audit.py` to a
constant made the audit-focused tests fail (**138 ran, 5 failed** —
hash-content recomputation, tamper localization at the exact index
in memory and after JSONL reload, the `/audit/verify` tamper
report, and the tamper negative control; basic prev_hash linkage
assertions hold even under a constant hash, recorded honestly in
`tests/README.md`); restored SHA-256-identical (`2c719311…`), full
suite green. The coordinator additionally re-ran the full suite
independently (**138 tests, OK**), re-verified the spec
reconciliation from the raw inputs, and re-drove the service live
(lockout, auditor boundaries, `/audit/verify`, chain tamper
localization) before treating the build as satisfying the tier.
One transient failure was observed and is recorded in
`tests/README.md`: on the first full run of the finished suite,
one auditor-over-HTTP test failed once, then passed standalone and
on five consecutive full runs (plus the coordinator's independent
run); no code was changed to work around it.

## Coverage statement (for this build)

- Specs: 6 / 6 forks spec'd (5 with at least one tagged claim; 11
  claims total; 1 enclave sheet with zero claims — Akamai Cloud).
- Core: 12 core functions implemented, at the High baseline, each
  with tracing tests; 6 tier uplifts implemented (hash-chained
  audit, chain-verification endpoint, fail-closed audit writes,
  audit query/reduction, logon lockout, auditor role).
- Extended: the functions specified and ranked, **not** implemented
  in this build: workflow/process automation engines (2 siblings),
  secure & encrypted transport beyond channel configuration (2),
  key & certificate lifecycle automation (1), voice/telephony/IVR
  media and conversation engines (1, plus Artera's virtual agents),
  email security & threat-detection engines (0 claims in this
  group; carried from the L2 union), AI/ML models and
  virtual-assistant intelligence (0), archiving & eDiscovery
  engines (0), correspondence & casework depth (0),
  personnel/asset tracking (0), permits/passes/surveys (0),
  e-signature execution (0), payment processing (0), and
  reporting/analytics engines beyond the records, search, and
  ack-status substrate. The group-specific long tail — fax
  transport networks (ECFax, ETHERFAX), patient-engagement
  automation (Artera), virtual-workspace streaming (Hypori),
  mission-critical communications ecosystems (Motorola MSFC), and
  edge delivery platforms (Akamai) — is named in the spec sheets.
- Baseline gaps named, not implied closed: MFA/authenticator
  management (IA-2(1)/(2), IA-5 — IdP layer), FIPS-validated crypto
  (SC-13), encryption at rest (SC-28), audit retention enforcement
  (AU-11), session lock/termination (AC-11/AC-12). Encryption is a
  platform note (TLS when a certificate is configured; at rest is a
  deployment-layer control).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Workflow / BPM engines (Artera, ETHERFAX claim the family)
  beyond the approval-less dispatch substrate.
- End-to-end encrypted message transport and secure data-exchange
  networks (ETHERFAX, Hypori); fax transport networks and carrier
  integration (ECFax, ETHERFAX).
- Key & certificate lifecycle automation (Hypori's certificate
  handling is the claim; CA connectors, issuance, deployment are
  the engine).
- Voice/telephony media, IVR and virtual-agent conversation
  engines (Artera), and mission-critical voice ecosystems
  (Motorola MSFC).
- Virtual-workspace streaming and remote-experience delivery
  (Hypori); edge delivery / CDN platform functions (Akamai).
- Email security & threat-detection engines, AI/ML models,
  archiving & eDiscovery engines, correspondence/casework depth,
  personnel/asset tracking, permits/passes/surveys, e-signature
  execution, payment processing, and reporting/analytics engines
  beyond the records substrate — carried from the Group 11 union
  (0 claims in this group's descriptions; named so the union is
  complete at this tier).

Platform layer (gap-listed, never implied closed): MFA /
authenticator management (IA-2(1)/(2), IA-5 — IdP layer);
FIPS-validated cryptography (SC-13 — not claimed; Python stdlib is
not a validated module); encryption at rest (SC-28 — deployment
layer); audit retention enforcement (AU-11); session lock /
termination (AC-11/AC-12 — per-request header auth holds no session
state); TLS only when a certificate is configured; multi-tenancy
(the build is a single-tenant reference deployment); demo
identities are hooks, not an IdP — IA-2 stays with the embedding
organization.
