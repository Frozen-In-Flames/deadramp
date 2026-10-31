# Communication — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Communication —
census unit `untiered:Communication` in `../../remainder.json`,
Untiered Set 13 built under the remainder pipeline. **This is an
untiered set, and that means something specific:** every member's
FedRAMP impact level is **Unknown** in the source dataset. The
source publishes no baseline for these offerings, so **tier stays
null**: no tier is assigned, no CMMC equivalence is drawn, and this
build asserts **no control baseline**. Per PIPELINE.md, untiered
offerings "build to their documented control claims; tier stays
null in the registry until the source publishes a baseline." The
union contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`,
pinned by tests.

The 2 forks were spec'd under the category's existing 21-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Communication L2 group's original
shipped claim tables exactly — **10 of 10 forks, 52 of 52 claims,
deep-equal** — before tagging this set. Result here: **3 claims**
across the set (5 raw hits, 2 removed under the founding group's
recorded correction classes — incident "events" are not scheduling,
and user-side "self-reporting" is an input, not reporting provided
by the offering; both removals recorded in
`scratch/ARTIFACTS.md`), **both forks claiming at least one**;
there is no zero-claim fork in this set.

The build implements the category's **twelve-function substrate**
— the messaging records machinery every sibling presupposes —
carried **byte-identical** from the founding Communication L2
build (`../communication-l2/src/comm/`, 7 of 7 modules; SHA-256
accounting below). The substrate is tier-independent records code:
the founding source contains no tier or baseline machinery, so
there was nothing tier-shaped to strip. Where the founding
contract's text ties the RBAC and audit functions to "the L2
baseline", read it here as **baseline-neutral substrate**: at tier
null they are carried as the parent design carries them, claimed
against no baseline.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| F1302271924 | BlackBerry | BlackBerry Cloud - AtHoc Services for Government | 1 |
| F1604017885 | Cisco Systems Inc. | Cisco Unified Communications Manager Cloud for Government (Cisco UCM Cloud for Government) | 2 |

In `forks.json` both forks are filed "Uncategorized (none in
source)"; the census assigned both to Communication from their own
descriptions, and the spec sheets record the assignment. Both
forks' recorded authorization status is FedRAMP In Process — a
status is record data, not a claim.

**Paired record, kept separate:** F1302271924A (the same AtHoc
product's "- High" record, filed under Collaboration at CMMC
L3-adjacent) is a separate registry offering, not a member of this
set; nothing in its record is attributed to this set's fork, whose
own record says impact Unknown. Pinned by test.

## The 12 core functions

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
   recorded in `skipped_recipients`; a message with zero
   deliverable recipients is rejected whole, consuming no ids.
5. **Delivery records** — one record (`dlv-`) per recipient ×
   channel kind, with a status lifecycle `queued → delivered |
   failed → acknowledged`, attempt counts, receipts, and failure
   reasons.
6. **Dispatch & receipts** — dispatch of due deliveries through a
   **reference transport**: a deterministic stub that marks a
   delivery `delivered` (with a receipt labelled
   `reference_transport: true`) when an enabled channel of its
   kind exists, else `failed` with
   `failure_reason='no_enabled_channel'`. It transmits nothing
   over any real network, and is labeled a stub in code, tests,
   and this README.
7. **Scheduling** — `send_at` on composition; `dispatch_due(now)`
   picks up everything due; dispatching a not-yet-due message is
   a validation error.
8. **Acknowledgement tracking** — messages may require
   acknowledgement; `acknowledge` is valid only on a delivered
   delivery of such a message; `ack_status` reports totals and
   pending recipients.
9. **Records & search** — message and delivery records are
   immutable once written; literal case-insensitive search across
   contacts, messages, and deliveries.
10. **REST API** — the full surface over HTTP (see the endpoint
    table below), with the house auth convention (X-User/X-Role
    against a demo registry; 401 unknown/mismatched, 403
    permission, denied attempts audited).
11. **Access control (RBAC)** — admin/operator/viewer matrix
    enforced in the store before any state change or id
    allocation, and again at the service layer.
12. **Audit log** — append-only, JSONL-persistable, recording
    every mutation and every denied attempt (`<action>:denied`).

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `ct-`, `grp-`,
`ch-`, `tpl-`, `msg-`, `dlv-`. Claim support in this set is
stated function by function in `UNION-SPEC.md`: **5 of the 12
functions are claim-supported** here (templates, composition,
delivery records, dispatch, scheduling); the other 7 are
**carried, not claimed**. Functions are carried as substrate; no
function is claimed to be *attained* by any fork — the build is
the merged open implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m comm serve --host 127.0.0.1 --port 8790
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from comm.access import User
from comm.audit import AuditLog
from comm.store import CommStore

audit = AuditLog()
store = CommStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "operator")
contact = store.create_contact("Dana", {"email": "dana@example.com"}, bob)
store.create_channel("email", "primary", admin)
msg = store.compose_message(bob, subject="Hi", body="Hello",
                            contact_ids=[contact["id"]],
                            channel_kinds=["email"])
print(store.dispatch_due(bob))  # {'dispatched': 1, 'delivered': 1, 'failed': 0}
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all reads + all writes, plus `channel_write`, `audit_read` |
| `bob`   | operator | all reads + `contact_write`, `group_write`, `template_write`, `message_compose`, `dispatch`, `ack_record` |
| `carol` | viewer   | reads only: `contact_read`, `channel_read`, `template_read`, `records_read` |

Read actions: `contact_read`, `channel_read`, `template_read`,
`records_read` (all roles). Write actions: `contact_write`,
`group_write`, `template_write`, `message_compose`, `dispatch`,
`ack_record` (operator + admin); `channel_write`, `audit_read`
(admin only). Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a
plain string carries identity but no role, so the service layer —
which knows the registry and always passes `User` objects — is
responsible for enforcement in that case (the founding group's
convention, carried unchanged).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/contacts` | contact_read | `{"contacts": [...]}` |
| POST | `/contacts` | contact_write | Body `{"name", "addresses"}` → 201 contact |
| GET | `/contacts/{id}` | contact_read | One contact |
| GET | `/groups` | contact_read | `{"groups": [...]}` |
| POST | `/groups` | group_write | Body `{"name"}` → 201 group |
| GET | `/groups/{id}/members` | contact_read | `{"members": [contact, ...]}` |
| POST | `/groups/{id}/members` | group_write | Body `{"contact_id"}` → 201 group |
| GET | `/channels` | channel_read | `{"channels": [...]}` |
| POST | `/channels` | channel_write | Body `{"kind", "name", "enabled"?}` → 201 channel |
| POST | `/channels/{id}/enabled` | channel_write | Body `{"enabled": bool}` → channel |
| GET | `/templates` | template_read | `{"templates": [...]}` |
| POST | `/templates` | template_write | Body `{"name", "subject", "body"}` → 201 template |
| GET | `/templates/{id}` | template_read | One template |
| GET | `/messages` | records_read | `{"messages": [...]}` |
| POST | `/messages` | message_compose | Body `{"subject"?, "body"?, "template_id"?, "variables"?, "contact_ids"?, "group_ids"?, "channel_kinds"?, "send_at"?, "require_ack"?}` → 201 message |
| GET | `/messages/{id}` | records_read | One message |
| GET | `/messages/{id}/deliveries` | records_read | `{"deliveries": [...]}` |
| GET | `/messages/{id}/ack-status` | records_read | `{message_id, require_ack, total, acknowledged, pending_contact_ids}` |
| POST | `/messages/{id}/dispatch` | dispatch | Dispatch that message → summary `{dispatched, delivered, failed}` |
| POST | `/dispatch-due` | dispatch | Dispatch all due queued deliveries → summary |
| POST | `/deliveries/{id}/ack` | ack_record | Acknowledge → delivery |
| GET | `/search?q=...` | records_read | `{contacts, messages, deliveries}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**100 tests, OK** at delivery: the founding group's 82-test core
suite carried with the code (its additions module, which pins a
different census unit, not carried), plus 18 spec tests pinning
this set (exactly 2 sheets; membership exact against
`remainder.json`; the High paired record excluded; every sheet's
tier null / impact "Unknown"; every claim's evidence verbatim in
its description; 3 claims total with no zero-claim fork; the two
adjudicated removals held removed; the recorded near-misses held
unclaimed). The category's signature send-gate mutation drill was
re-run in this tree — exactly 4 failures under the mutant, store
restored and SHA-256 verified (see `tests/README.md`). A live
smoke also passed: health ok, contact → channel → message →
dispatch delivered with the receipt labelled
`reference_transport: true`, acknowledgement recorded, a viewer
write denied 403 and the denial present in the audit log.

## Byte-identity accounting

`src/comm/` is carried from the founding group
`../communication-l2/src/comm/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `35d08d68f86790f8d9742bcfe27dc22894a1d0f0abe3b1cbf16d6b98e9f6810a` |
| `__main__.py` | `54fa68bdd364626f034808290388b23f82f89e784c08d848eb4b9b0c95696dd7` |
| `access.py` | `aaf4dcc3d4100d7fe02543a0c1b8da724ca428541f44f56a89932ff10c63f0a4` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `e928aa7318b629f3d69b5d80ec2b192015f1fafa5d6929ab1eec523d16e7a0d6` |
| `service.py` | `af46b6ebe581c76b003685af7f35d567e6b509a021de79fd5f1653539afea9d6` |
| `store.py` | `6ccd412c2c1a836694d74687804aa90abe31f4c54eba62e916c31cb6dc5e6110` |

The test suite is likewise carried (the founding suite minus its
additions module, which pins a different census unit), with one
labeling fix in `tests/comm_helpers.py` (its docstring now names
this untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under prose
that carries control language. A documented control claim is a
**fork's claim about itself**, recorded with its evidence in
`UNION-SPEC.md` and `specs/specs.json`; it is not the build's
control attainment, and nothing here fills a family in from any
baseline.

Documented in part by at least one fork in the set, at the prose
tier:

- **Access control (AC), in part** — 2 forks, at prose weight:
  BlackBerry AtHoc ("create their own permission-based network")
  and Cisco UCM Cloud ("create personalized access lists, and
  give access to all your corporate collaboration features").
  Neither sentence carries the taxonomy's `identity_access`
  phrases, so that family stands at 0 of 2 in the claim table;
  this record does not change that.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, AU, CA, CM, CP, IA, IR, MA,
MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control claims** — is
asserted by no description in the set. In particular: no
description carries a login, authentication, SSO, or
identity-proofing phrase (IA); no description asserts encryption
— AtHoc's "communicate and collaborate securely" is an adverb,
its "safeguards important personal information" is safeguarding
prose with no framework language, and Cisco's "government-level
security" is posture prose (SC); and no description carries audit
language in any form (AU). If the source later publishes an
impact level for any of these offerings, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented
  control language is recorded as *its* claim, never as the
  build's control attainment.
- **The reference transport is a deterministic stub.** Dispatch
  records delivery locally — status, attempts, and a receipt
  explicitly labelled `{"transport": "reference",
  "reference_transport": true}` — when an enabled channel of the
  delivery's kind exists. **It does not transmit anything over
  any real network**: no email is sent, no SMS is sent, no call
  is placed, no push notification is pushed. There is no real
  channel anywhere in this build.
- **Extended functions are specified, not implemented.** The
  union spec ranks 21 functions; the substrate behind 12 is
  implemented here. NOT implemented (substance counts are this
  set's): video conferencing, meetings & real-time media
  transport (Cisco substance throughout; no taxonomy family
  exists for it); voice/telephony media and call-control engines
  (Cisco — the claim tags call *records* substrate weight, the
  media is not built); presence & availability services and
  desktop sharing (Cisco substance); crisis-communication
  orchestration and multi-channel alerting engines (AtHoc —
  dispatch of composed messages is Core, alerting campaigns are
  not); personnel accountability, location/status visibility &
  field-reporting platforms (AtHoc substance; its family stands
  at 0); inter-organizational federated communication networks
  (AtHoc Connect substance); voicemail & unified messaging
  engines (Cisco substance beyond the records claim); real
  channel transports of any kind.
- **Named absences stand.** Video conferencing has no family
  and 0 claims; delivery verification has 0 of 2 (no
  "acknowledg" occurs in either description, AtHoc's
  accountability substance notwithstanding); tracking stands at
  0 with its substance present in other words; audit stands at
  0 of 2 in descriptive text. Nothing was back-filled to make
  the set look complete, and the two removed raw hits are
  recorded as removals, not silently dropped.
- **The build performs no cryptography of its own.** No fork in
  this set documents an encryption claim; the substrate does no
  encryption — TLS is a deployment-layer option when a
  certificate is configured, and FIPS-validated crypto (SC-13)
  is not claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  and `carol` are documented demo identities supplied by header;
  the service enforces the role permission matrix on those hooks
  and ships no identity provider, no credential store, and no
  authentication of its own.
