# Final GAPS batch — Remainder Addition — Collaboration L2 (+3 forks)

This note records the second GAPS-batch unit in this group
directory: the closure of the 5 open entries of the GAPS.md
section "Remainder Addition — Collaboration L2 (+3 forks)"
(inventory idx 595–599) — the new gap functions `ADDENDUM.md`
section 5 registered when the remainder forks Webex for
Government, Huddle, and IdeaScale Gov joined the founding union.
The first batch unit's note is `BATCH.md` (idx 14–20 and 22);
this unit covers idx 595–599 in `../../gaps-batch/inventory.json`.

**No re-judgments.** The drafted dispositions held on close
reading of `ADDENDUM.md` section 5 and the group's specs: the 2
build-extension entries land as in-substrate records extensions
and the 3 stub-engine entries land as labeled reference
implementations. `DECISION.md` qualification 1 was not needed.

## What was built

One new module, `src/collab/extensions_addition.py`, adding a
second wrapper class `CollabExtensionsAddition` over the core
`CollabStore`, independent of the first unit's
`CollabExtensions`. Conventions follow the first unit exactly:
actor-first signatures; core state read and validated only
through the core store's public API; no operation writes core
state; the workspace membership boundary binds every operation
because each resolves its workspace through the core store;
validation precedes mutation (a failed operation consumes no id
and changes nothing); creation is audit-before-commit on the
core's plain append-only audit log (an audit write failure
changes nothing and consumes no id). This unit's mutations are
audited under the `exta_` action prefix, distinct from the first
unit's `ext_`, so the two units' audit trails stay
distinguishable. Moderate apparatus held: no hash-chained audit,
no auditor role (the High tier's uplifts).

One deliberate form difference from the first unit, recorded
here rather than hidden: writes on the administration-console
surface (idx 596) map to the core `admin` action — the
platform-administrator action only the admin role holds —
because a centralized administration console is operated by
administrators. Every other surface in this module maps writes
to the core `post` action, as in the first unit; reads bind the
`read` permission through the core workspace resolution, as
everywhere in this build.

Every pre-existing module — the 7 core modules and the first
unit's `extensions.py` — is byte-identical to the shipped build
(SHA-256 checked after the build; `store.py` still reads
`d2b943e2…`, `extensions.py` still reads `dfcd2c8d…`).

Suite: 242 tests before, 280 after, all green. Fresh negative
control: the idea current-state derivation
(`_current_idea_label`) — the live drill produced exactly 6
not-passing tests (2 failures + 4 errors), all in
`tests/test_gaps_batch_addition.py`; see `tests/README.md` for
the record and `TestNegativeControlIdeaDerivation` for the
standing three-legged control.

## Per-entry disposition

### idx 595 — "Innovation management & crowdsourcing platform (IdeaScale)" — build-extension → **built**

Campaign records (`inc-`, `campaign_ref` unique per workspace),
idea records (`idea-`, `idea_ref` unique per campaign; the idea
is workspace content contributed by a member, like a board card,
and its short text is its title), append-only idea-state records
(`ist-`) over a fixed reported-label vocabulary, endorsement
records (`sup-`) over opaque stakeholder references (a
campaign's crowd is wider than the workspace roster, which
belongs to the embedding organization; a duplicate endorsement
by the same supporter of the same idea is refused), and plan-link
records (`pln-`). An idea's current state is derived at read from
its recorded labels (default `reported_submitted`) and stored
nowhere — the stored idea record carries no state key, pinned by
test. The transformation of input into project plans — the
fork's own closing move, per `ADDENDUM.md` — is recorded as a
link from the idea to a core board: refused whole with
`ValidationError` while the derived current state is not
`reported_adopted`, duplicate links refused, and recording a
link changes no core board record (pinned deep-equal). Plan
content is authored by members on the board; nothing is
generated here (`generated_here: False`). `campaign_view` and
`idea_view` derive exact counts and per-state counts at read;
counts and states only — no score-shaped key exists anywhere in
any view (pinned by a recursive key scan).

### idx 596 — "Centralized administration console for collaboration services (Webex)" — build-extension → **built**

Administered-service records (`svc-`, `service_ref` unique per
workspace), configuration revision records (`svr-`) holding
settings as data (a flat string-to-string mapping, validated;
nested structures and non-string values rejected), administrative
action records (`adm-`, action label and opaque target held
verbatim, outcome from a fixed reported-label vocabulary,
`effected_here: False`), and a `console_view` deriving exact
service / revision / action counts and the latest action label
at read. The stored service record holds no settings key
(pinned): settings live only in the append-only revisions, and
the current settings are derived at read from the latest
revision — a new revision changes the view without touching the
service record. Recording a revision applies nothing anywhere
(`applied_here: False`): the platform applies configuration, and
effecting an administrative action on a named external system is
the platform's work; this build records. The console is a
records function registered in its own name in `ADDENDUM.md`
section 5, so PLATFORM-LAYER.md decision 6 (console surfaces as
deployment properties *unless* a group's spec claims a records
function for them) does not close it — the claimed records
function is what is built here. Console writes map to the core
`admin` action (see the form note above); a member's or viewer's
attempt is denied and the denial is audited
(`exta_admin_service_register:denied`, pinned by test).

### idx 597 — "Virtual visitation scheduling portal: business-rules / workflow configuration, zero-touch device connectivity (Webex)" — stub-engine → **reference**

Labeled reference implementation (`reference_stub: True`
throughout). Visit records (`vst-`) bind the portal's visits to
core calendar events — the scheduling surface the portal
presupposes is the Core calendaring function, so a visit record
validates its event through the core store and treats an event
from another workspace as not found; visitor and visited
participant are opaque references (they are not workspace
members). The visit itself is conducted elsewhere
(`conducted_here: False`, `media_here: False`, and
`reference_transport: True`): no media exists in this build.
Reported outcome records (`vso-`) hold the platform's labels
verbatim, with the latest derived at read in `visit_view`.
Business-rule / workflow configuration lands as definition
records (`vrul-`, kind `business_rule` or `workflow`, steps held
as data) that are never run, triggered, or evaluated — the house
registry-never-executes doctrine, pinned behaviorally
(registering a definition leaves the core event list
deep-equal). Zero-touch device connectivity lands as connection
report records (`vcon-`, `reference_transport: True`,
`connected_here: False`, `provisioned_here: False`): the device
is an opaque reference, may be reported against a visit, and the
outcome is the platform's reported label — provisioning and
connection happen on the platform, never here.

### idx 598 — "Collaboration hardware endpoints & purpose-built devices (Webex, platform layer)" — stub-engine → **reference**

Labeled reference implementation, as drafted. Endpoint
registration records (`dve-`, opaque `device_ref` plus a kind
label from a fixed vocabulary) and append-only reported-status
records (`dvs-`); the endpoint's current status is derived at
read from the latest reported label and stored nowhere (the
stored registration carries no status key, pinned). The devices
are manufactured hardware — the entry's own GAPS.md text and
`ADDENDUM.md` section 5 both name them platform layer — so
nothing is manufactured, provisioned, or connected here
(`manufactured_here: False`, `connected_here: False` on every
registration). What a software build can honestly hold for
purpose-built devices is the registry and status-report surface,
and it ships labeled reference because the endpoints' operation
(media, provisioning, firmware) sits entirely outside this
records substrate.

### idx 599 — "Product-specific connector engines (Huddle, office-suite integrations)" — stub-engine → **reference**

Labeled reference implementation. Connector definition records
(`con-`, `connector_ref` unique per workspace; `product_label`
is the caller's verbatim name for the connected product, held as
data — the module itself names no third-party product) and
exchange records (`cex-`). An exchange names the exchanged
object by opaque reference only, optionally bound to a core file
record validated through the core store; no content is held
(`content_held: False`, and no field can hold it — pinned) and
nothing is transmitted from here (`transmitted_here: False`,
`reference_transport: True` on every record). The outcome is the
connector's reported label; `connector_view` derives exact
exchange counts and per-outcome counts at read. Core 9 (the
service is a REST API) stays the integration surface; the
engines into named products run on the platform, per
`ADDENDUM.md` section 5's Group 33 connector-gap precedent.

## Tier discipline record

- Baseline held: the Moderate baseline (800-53 Rev. 5 Moderate /
  CMMC L2) is neither raised nor lowered by this unit; no L3
  apparatus (hash-chained audit, auditor role) and no L1 audit
  caveat were imported.
- The platform-layer items stay where PLATFORM-LAYER.md puts
  them: identity stays with the embedding organization (decision
  1; demo identities are hooks, not an IdP), no FIPS-validated
  cryptography is claimed (decision 2), and session policy
  belongs to the embedding organization's access layer (decision
  5). Decision 6 is addressed at idx 596: the console is claimed
  as a records function in its own name, so it is built, not
  closed by the umbrella.
- What is still not here, by design: no visit is conducted and
  no media exists, no rule or definition is executed, no device
  is provisioned or connected, no configuration is applied, no
  content crosses a connector, and nothing is deleted anywhere.

## Verification (builder side)

- Full suite before: 242 tests, OK. After: 280 tests, OK.
- Core byte-identity: SHA-256 of all 8 pre-existing
  `src/collab/` modules verified unchanged after the build
  against the pre-build record in `scratch/`; `extensions.py`
  (the first unit's) is among them. `extensions_addition.py` is
  the only new source file, and `test_gaps_batch_addition.py`
  the only new test file.
- Mutation drill on the fresh negative control: backup to
  `scratch/extensions_addition.py.premutation`, patched
  `_current_idea_label`'s return at its own line (line 417; the
  line text occurs exactly once in the module) from
  `states[-1]` to `states[0]`, suite ran 280 with exactly 6 not
  passing (2 failures + 4 errors), all in
  `tests/test_gaps_batch_addition.py`; restored from backup,
  SHA-256 verified identical (`0de608d9…`), suite re-run green.
  Raw output: `scratch/addition_mutation_run.txt`.
