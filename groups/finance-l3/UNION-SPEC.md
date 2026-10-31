# Union Spec — Finance, CMMC L3-adjacent (DeadRamp Phase 2, Group 42 singleton)

The singleton spec for the Finance category at the L3-adjacent
tier: **1 fork, FedRAMP High** — AWS GovCloud (Amazon Web
Services, Inc.). Reconciled zero-diff: `specs/specs.json` ↔
`forks.json` category="Finance" + cmmc_tier="L3-adjacent" (exactly
one match) ↔ MAP.md's category arithmetic (Finance totals 4
offerings = 2 at L2, shipped as Group 31 + 1 at L3-adjacent, this
singleton + 1 untiered, Emburse Enterprise with impact Unknown and
tier null, a remainder fork). MAP.md's sibling sections list only
groups of size 2+, so no sibling-section diff applies to a
singleton; forks.json exactness plus the category arithmetic is
the reconciliation, per the earlier singleton builds. The
reconciliation is asserted programmatically in
`scratch/extract.py`.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two
parents:

1. The **Group 31 merged build** (`../finance-l2/`) — the union of
   the 2 Finance L2 (FedRAMP Moderate) forks, shipped as a working
   clean-room finance records service (11 core functions).
2. This singleton's **1 High fork**, via the spec sheet in
   `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** /
CMMC **L3-adjacent** — and must satisfy it **in full** (Rule 2),
this document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run
independently by the coordinator, and both negative controls were
mutation-verified by patching the implementation (see
tests/README.md).

**Reuse, stated explicitly:** this build reuses Group 31's own
open-source code (Apache-2.0, ours). One module is byte-identical
to Group 31 (`__init__.py`, SHA-256
`bfbdf5a40d665f74aca1511a7573cd52202b3954ed83040c696162a839e10b54`);
six are modified for the tier uplift (`errors.py` —
AuditWriteError added; `access.py` — auditor role added;
`audit.py` — wholesale port of the proven hash-chain / fail-closed
/ query uplift from `groups/crm-l3`, itself the
`groups/analytics-l3` mechanics; `store.py` — snapshot fail-closed
wrapper added, following `groups/accounting-l3`; `service.py` —
lockout, audit verify/query, auditor user added; `__main__.py` —
auditor user and lockout flags added). No core function changed
behavior: every Group 31 test passes with only the documented
uplift adaptations (tests/README.md).

## How functions were counted — zero claims, honestly

Group 31's 8-family taxonomy was applied **verbatim** (same ids,
labels, and matching patterns, in `scratch/extract.py`) to this
fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22). A family is
claimed only when the offering's own description contains matching
text; the first matching sentence would be stored in
`specs/specs.json` as evidence.

**Result: 0 claims.** The fork is a cloud infrastructure platform
filed under Finance. Its description is seven sentences of region
and platform prose: an AWS Region for sensitive government
workloads, FedRAMP and ITAR compliance statements, US-citizen /
US-soil operation of the US-East and US-West Regions, eligibility
screening of root account holders, an inventory of the region's
data-center / server / networking substance, and an invitation to
collaborative continuous monitoring. No sentence contains any
taxonomy family's matching text — no earned wages, no wellness, no
booking, no spend, no reporting, no open-platform phrase, and not
even the `hosting_platform` family's verbatim phrases ("SaaS
offering", "multi-tenant"). The full description is preserved
verbatim in the spec sheet, and no function was invented for it.
Counts are a floor, and here the floor is zero — the same honest
outcome as the zero-claim sheets in Groups 28 and 35 and
Singletons 38 and 40.

Near-misses, recorded in full in `scratch/ARTIFACTS.md`, not
rounded up: "move more sensitive workloads into the cloud" is not
the verbatim hosting claim; "collaborative continuous monitoring"
matches no family in this taxonomy (Finance has no monitoring
family); the root-account screening sentence is eligibility prose,
not a finance function; the infrastructure inventory of sentence 6
is the fork's actual substance and it is platform-layer, never
rounded up into finance families; and the source record's
`business_categories` names "Finance" first among ten labels —
that label is why the offering is filed in this category, and per
Group 31's correction 5 a source category label is not a
functional claim. The raw record's per-service catalog (hundreds
of individual AWS services with their own descriptions) is record
data about the platform's service inventory, not the offering's
marketplace description; following the Group 40 precedent (record
fields are not description text), it tags nothing here and is
named at the platform layer in the gap list.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Earned wage access (on-demand pay) | **Core** (records) — carried from the Group 31 union (claimed 1 of 2 there); instant money movement is Extended |
| 1 | 0 | Financial wellness solutions | **Core** (offering registry + enrollment records) — carried from the Group 31 union (claimed 1 of 2 there); the wellness tools themselves are Extended |
| 1 | 0 | Travel booking (air & hotel) | **Core** (booking *records*) — carried from the Group 31 union (claimed 1 of 2 there); live inventory/ticketing is Extended |
| 1 | 0 | Group & meeting travel management | **Core** (the program/traveler/booking substrate) — carried from the Group 31 union (claimed 1 of 2 there) |
| 1 | 0 | Spend management | **Core** (budgets, spend-vs-budget from records) — carried from the Group 31 union (claimed 1 of 2 there) |
| 1 | 0 | Reporting & analytics | **Core** (program summaries computed on read) — carried from the Group 31 union (claimed 1 of 2 there); streaming pipelines are Extended |
| 1 | 0 | Open platform & APIs | **Core** (the service is API-first) — carried from the Group 31 union (claimed 1 of 2 there) |
| 1 | 0 | SaaS / cloud delivery (platform note) | Platform layer — near-miss recorded (verbatim patterns absent); the hosting platform itself is this fork's substance and is not a function of this build |

Baseline families carried at zero claims in this category at both
tiers (they are in the Core as baseline hooks, exactly as in Group
31, now uplifted to High): access control & authentication,
workflow & approvals (the access-request state machine with
separation of duties), and the audit trail.

Named here so the category record is complete — functions a
"Finance" label suggests that **no fork in this category claims at
either tier** (zero claims; excluded from the union, not silently
dropped, not gaps): banking integration & account verification;
payroll system integration & wage calculation; lending & credit;
trading & investment execution; tax reporting & remittance; GRC
platform functions (present at L2 only as a source category label
on Groupize's record).

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35 and Singleton 40 precedent).** This fork tags zero
claims, yet all 11 core functions stand in this build. The
reasoning is the Merge Rule itself, not convenience: a cross-tier
merge takes the union of the parents upward whole, and Group 31's
union — the category substrate this fork's category presupposes —
is a parent of this build. A wording artifact (an infrastructure
platform filed under a finance label, its description written in
region prose with no taxonomy vocabulary) is not a downgrade, and
stripping the substrate at High because the High fork's marketing
prose contains no finance functions at all would dilute the
union, which Rule 1 prohibits. Every core function is therefore
flagged **carried, not claimed** for this tier. Where the fork
claims less than the substrate — which here is everywhere — that
is this paragraph, stated once and plainly, rather than eleven
quiet exceptions. The fork's own substance is not finance
function and is not built: it is the platform layer, named in
Gaps below.

## The Core — what the merged build implements (11 functions, at the High baseline)

The same 11 functions as Group 31, carried up whole. The three
disciplines of Group 31 carry unchanged: **integer cents only**
(every `*_cents` amount is a Python `int`; booleans and floats are
rejected at the boundary, so all arithmetic is exact);
**records, not execution** (payments, transfers, disbursements and
bookings are recorded, never executed against real rails — this
build moves no money and books no travel); **opaque references
only** (participants carry a `ref` string and a kind, nothing
else; no entity shape has a field that could hold a real name,
bank account number, card number, or government identifier, and
the shapes are pinned by tests).

1. **Programs & members** — named programs with an owner, a
   member list, and provenance. Membership is the boundary every
   other core function enforces. Carried, not claimed.
2. **Participant & traveler registry (opaque references)** —
   participants known only by an opaque `ref` and a kind
   (`employee` or `traveler`), with active/inactive status.
   Carried, not claimed.
3. **Earned-wage accrual & access records** — accruals per
   participant per pay period (`YYYY-MM`); access requests run
   the approval machine under the **earned-cap invariant**
   (pending plus approved plus disbursed for a period never
   exceed that period's earned amount, enforced at request time
   by `_check_access_cap`); approving is separated from
   requesting; a disbursement record records, after the fact,
   that an approved amount moved on external rails. Derived
   amounts are computed on read, never stored. Carried from the
   Group 31 union.
4. **Travel booking records** — booking records (air or hotel,
   date range, integer cents) with a `recorded → confirmed /
   cancelled` lifecycle. Records of reservations made elsewhere.
   Carried from the Group 31 union.
5. **Spend budgets & tracking** — a budget per program per
   period; spend-vs-budget computed from records (non-cancelled
   bookings by kind; disbursed wage access under the
   `earned_wage` category), with variance and over-budget flags —
   computed, never asserted. Carried from the Group 31 union.
6. **Financial wellness offering registry** — offerings (title +
   kind: education, coaching, budgeting, savings, counseling)
   with participant enrollment records. Carried from the Group
   31 union.
7. **Reporting** — a per-period program summary computed on read
   from records only (participant count; earned / accessed /
   disbursed / pending wage totals; booking counts and totals by
   kind; wellness enrollment count). Carried from the Group 31
   union.
8. **Workflow & approvals** — the access-request state machine:
   `requested → approved / denied`, `approved → disbursed` (via
   a disbursement record), `requested / denied → void`. Decision
   requires an actor other than the request's creator
   (separation of duties, AC-5); void is limited to the creator,
   the program owner, or a platform admin. Carried, not claimed.
9. **API access** — every function above over a REST API (JSON).
   Carried, not claimed — uplifted with lockout (below).
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` **plus the `auditor` role**
    [L3], layered with program membership (non-members cannot
    read or write a program's content; the platform `admin` role
    can). Carried, not claimed — uplifted to High.
11. **Audit log** — an append-only audit trail of every mutation
    and every denied attempt, **hash-chained**, JSONL-persistable,
    **fail-closed**, and **queryable** [L3]. Carried, not claimed
    — uplifted to High.

## Implementation contract deltas [L3]

The implementation contract is Group 31's (`../finance-l2/
UNION-SPEC.md`), unchanged except for the uplift deltas:

- `finance/errors.py` — adds `AuditWriteError(FinanceError)`,
  raised by `AuditLog.record` when the JSONL append fails.
- `finance/audit.py` — entries additionally carry `seq`,
  `prev_hash`, `hash` (SHA-256 of the canonical JSON of
  `{seq, ts, actor, action, target, details, prev_hash}`; genesis
  `prev_hash` = `"0" * 64`). `record()` rolls back the in-memory
  append and raises `AuditWriteError` on `OSError` (AU-5).
  `.verify_chain()` returns `(ok, first_bad_index_or_None)`.
  `.query(actor=None, action=None, target=None, since=None,
  until=None)` returns filtered entries (AU-7).
- `finance/access.py` — roles are `admin|member|viewer|auditor`;
  `auditor` = `{audit_read}` and nothing else (AC-5). Existing
  roles' permission sets are unchanged.
- `finance/store.py` — every public mutating method (exactly the
  15 methods that record audit entries) is wrapped by
  `_fail_closed`: the method runs against a deep-copy snapshot of
  the store state (records and id counters); on `AuditWriteError`
  the snapshot is restored in full and the error propagates.
  `_check_access_cap` and all other L2 behavior are unchanged.
- `finance/service.py` — `make_server(host, port, store, audit,
  users, max_failures=3, lockout_seconds=300)` [L3 kwargs].
  Consecutive auth failures are tracked per username; at
  `max_failures` the username locks for `lockout_seconds` (403,
  audited `auth:locked`); success resets the counter (AC-7). The
  service's own audit helper re-raises `AuditWriteError` instead
  of swallowing it (AU-5). New routes: `GET /audit/verify` →
  `{ok, entries, first_bad_index}` (audit_read; the entry count
  is read before the request's own `audit_read` entry is
  appended), and `GET /audit` accepts optional `actor`, `action`,
  `target`, `since`, `until` filter parameters (AU-7).
  `AuditWriteError` from a store operation lands in the existing
  `FinanceError` arm of `_dispatch` (400 — not a success), as in
  the proven pattern.
- `finance/__main__.py` — demo users `alice=admin, bob=member,
  carol=viewer, dana=auditor` [L3] and flags
  `--max-failed-logins N` / `--lockout-seconds S` [L3].

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High**
  (per `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline
  (the FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110
  practices of NIST SP 800-171 Rev. 2 **plus** the selected NIST
  SP 800-172 enhanced requirements. The cross-tier parent (Group
  31's build) sat at Moderate; the union baseline is therefore
  the High baseline, un-diluted (Merge Rule 1), inherited in full
  (Rule 2). "Adjacent" remains deliberate wording, as in the
  crosswalk: L3 is not identical to FedRAMP High; it is the same
  assurance weight class.
- **Feature → control family mapping (carried from Group 31,
  with the uplifts):**

  | Core function | Control families | How the build answers |
  |---|---|---|
  | Programs, membership, participants | AC-2, AC-3, AC-6, IA-2 (hooks) | Platform roles layered with program membership; participants keyed by opaque references, shapes pinned by tests |
  | Accruals, access, disbursements, bookings, budgets | SI-10, SC-8 | Integer-cent validation and the earned-cap invariant reject malformed or over-cap input whole, never partially applied; TLS when a certificate is configured |
  | Workflow & approvals | AC-5 | The decider of an access request is never its creator, enforced in the store; the auditor role separates audit review from administration |
  | Reporting | AU-6 | Summaries computed on read from records only |
  | API access | AC-3, AC-7 [L3] | Per-request header auth against the registry, with unsuccessful-logon lockout |
  | Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 [L3 depth] | Append-only, hash-chained, fail-closed, queryable log including denied attempts; no mutation API |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Group 31, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. This build does **not** inherit the fork's own FIPS posture — validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only: **FedRAMP authorizes
  products; CMMC certifies organizations** — the build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither regime accepts the other as evidence. Any real
  compliance claim still has to be earned inside each regime
  separately.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (0 tagged claims; full description
  preserved; near-misses itemized in `scratch/ARTIFACTS.md`).
- Core implemented: **11 / 11** functions above, carried up whole
  at the High baseline and flagged carried, not claimed; 6 tier
  uplifts implemented (hash-chained audit, fail-closed audit
  writes with store rollback, audit query/reduction, chain
  verification endpoint, logon lockout, auditor role).
- Tests: **249** (202 inherited from Group 31, 7 added inside
  inherited files, 40 in new uplift files); two negative controls,
  both mutation-verified live (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own substance (platform layer; the fork's actual
product surface — none of it is finance function and none of it is
built here):

- The cloud infrastructure platform itself: the GovCloud
  (US-East) and (US-West) Regions — compute, storage, networking,
  database, and the rest of the provider's service catalog (the
  raw record lists its services individually) operated as
  infrastructure. This build runs *on* such a layer; it does not
  implement one.
- Region operations & sovereignty properties: US-citizen /
  US-soil operation, the ITAR-regulated environment, and the
  FedRAMP High authorization boundary of the regions themselves.
- Eligibility screening of root account holders (description
  sentence 5) — the platform's customer-screening operation.
- Collaborative continuous monitoring with the provider
  (description sentence 7) — a provider-side monitoring
  arrangement, not a function of this build.

Extended functions carried from the Group 31 union, not
implemented:

- Instant disbursement execution / payment rails (ACH, wire,
  card networks) — the execution remainder of earned wage access.
- Travel booking execution engines (live air/hotel inventory,
  ticketing, reservation systems).
- Financial wellness delivery tools (the budgeting, coaching,
  and savings products behind the offering registry).
- Streaming / real-time reporting pipelines.

Baseline gaps at High (platform layer; gap-listed, never implied
closed): MFA / authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13); encryption at rest (SC-28);
audit retention enforcement (AU-11); session lock / termination
(AC-11/AC-12). Platform notes: multi-tenancy (the fork operates
multi-tenant regions in reality; this build is a single-tenant
reference deployment); TLS only when a certificate is configured;
demo identities are hooks, not an IdP (IA-2 stays with the
embedding organization). The infrastructure platform the fork
asserts in prose is the deployment layer itself.
