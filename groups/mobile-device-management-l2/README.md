# Mobile Device Management (MDM) L2 — merged build (Operation DeadRamp, Phase 2, Group 50)

This is the merged, clean-room implementation of the **Mobile
Device Management (MDM) L2** singleton: **1 fork / vendor
platform** from the FedRAMP Marketplace (Network Inventory and
Optimization Solution (NiOS®), Turning Point Global Solutions,
L.L.C.), built as one open-source service from the group's union
contract (`UNION-SPEC.md`). MDM is a brand-new category with no
parent group at any tier, so the function taxonomy was defined
from the fork's own marketplace description (the Group 1
method): **16 claims**, each carrying its source sentence as
evidence.

**What the fork actually is:** by its own description, a
**Telecommunication Expense Management (TEM) and Managed
Mobility (MM) system** — telecom ordering, service inventory,
bill validation, budgets, and reporting — filed under MDM. Its
description contains no device-management vocabulary (no
enrollment, wipe, device policy, or handset registry), and this
build does not invent any: it implements the TEM/MM records
substrate the description claims. The category's device-control
surface is named as Extended gaps in `UNION-SPEC.md`.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 14 core functions

1. **Customer organizations & membership** — organizations
   (`org-`) known only by an opaque `ref` and a label, with an
   owner and member list; membership bounds every other
   function.
2. **Telecom service inventory** — items (`inv-`) for wireline,
   mobility, and other services, with opaque refs and monthly
   recurring charges in integer cents. The record shape is
   pinned: **no field can hold a phone number, IMEI, serial, or
   any real device identifier**. Provisioning state changes only
   through fulfilled orders.
3. **Service order records & lifecycle** — orders (`ord-`):
   `new`, `macd`, `port`, `suspend`, `restore`, `disconnect`,
   through `requested → approved → fulfilled` (plus `rejected`,
   `cancelled`). The decider is never the requester
   (separation of duties); fulfillment moves the linked item's
   provisioning state per the spec's fixed mapping.
4. **Workflow definition registry** — definitions (`wfl-`)
   registered as data. The registry **never executes** one;
   that is pinned by test.
5. **Contract & quote registries** — contracts (`con-`) by
   opaque ref with a term window; quotes (`quo-`) recorded
   against contracts — the records validation verifies against.
6. **Bill records & validation runs** — bills (`bil-`) by
   `YYYY-MM` period with stated totals in integer cents;
   validation runs (`val-`) record stated vs. expected (summed
   from the inventory registry under a stated rule), the
   variance, and the result. A run never modifies the bill.
7. **Dispute records & lifecycle** — disputes (`dis-`) with
   reasons and resolutions recorded verbatim, tracked
   `open → in_progress → resolved`. A dispute can never exceed
   its bill — rejected whole, no id consumed.
8. **Budgets & derived availability** — budgets (`bud-`), one
   per organization and period; obligations (`obl-`) record
   obligated and spent amounts. Obligated, spent, and available
   are **derived at read, never stored** — the stored budget
   record carries no such key. Projections are caller-supplied
   values recorded verbatim; nothing computes one.
9. **Chargeback records** — internal customer chargebacks
   (`chg-`) against budgets, by opaque unit reference.
10. **Budget alert records** — alerts (`alr-`) recorded by kind
    with acknowledgements. Recorded, not delivered.
11. **Search & summary reporting** — substring search across
    accessible organizations, inventory, orders, bills, and
    contracts; per-organization summaries computed on read as
    counts and money sums. Never scores.
12. **REST API** — every function above over a JSON REST API.
13. **RBAC** — roles `admin`, `member`, `viewer` with a
    permission matrix enforced on every operation, layered with
    organization membership.
14. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). All money is integer cents: floats, booleans, and
strings are rejected at the boundary.

## Run

```bash
cd groups/mobile-device-management-l2
PYTHONPATH=src python3 -m mdm serve            # http://127.0.0.1:8000
PYTHONPATH=src python3 -m mdm serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m mdm serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | member | organizations, records, decisions (never on his own orders) |
| `carol` | viewer | reads only |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | read | `{"organizations": [...], "inventory": [...], "orders": [...], "bills": [...], "contracts": [...]}` |
| `GET /organizations` · `POST /organizations` | read / create_org | create → 201 |
| `GET /organizations/{id}` · `POST /organizations/{id}` | read / enter | POST updates the label |
| `POST /organizations/{id}/members` | manage_members | body `{"username": ...}` |
| `GET /organizations/{id}/summary` | read | counts and sums, computed on read |
| `GET /organizations/{id}/inventory` · `POST` | read / enter | `?service_kind=`, `?state=` filters; create → 201 |
| `GET /inventory/{id}` | read | |
| `GET /organizations/{id}/orders` · `POST` | read / enter | `?status=` filter; create → 201 |
| `GET /orders/{id}` | read | |
| `POST /orders/{id}/approve` · `/reject` | decide | never the requester |
| `POST /orders/{id}/cancel` · `/fulfill` | enter / record | fulfillment moves provisioning state |
| `GET /organizations/{id}/workflows` · `POST` · `GET /workflows/{id}` | read / record | definitions only; never executed |
| `GET /organizations/{id}/contracts` · `POST` · `GET /contracts/{id}` | read / enter | |
| `GET /organizations/{id}/quotes` · `POST` | read / enter | |
| `GET /organizations/{id}/bills` · `POST` · `GET /bills/{id}` | read / enter | |
| `POST /bills/{id}/validate` · `GET /bills/{id}/validations` | record / read | validation runs |
| `GET /bills/{id}/disputes` · `POST` · `GET /disputes/{id}` | read / enter | |
| `POST /disputes/{id}/start` · `/resolve` | record / decide | resolution verbatim |
| `GET /organizations/{id}/budgets` · `POST` · `GET /budgets/{id}` | read / enter | derived `obligated_cents`, `spent_cents`, `available_cents` on reads |
| `GET /budgets/{id}/obligations` · `POST` | read / record | kinds `obligated`, `spent` |
| `GET /budgets/{id}/chargebacks` · `POST` | read / record | |
| `GET /organizations/{id}/alerts` · `POST` | read / record | recorded, not delivered |
| `POST /alerts/{id}/acknowledge` | record | |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/mobile-device-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 75 tests
```

**75 tests, all passing**, including the mutation-verified
negative control: stubbing the availability derivation in the
real store to return the bare budget makes exactly 4 tests fail
(see `tests/README.md` for the drill record).

## Honesty

- The build implements the records substrate the fork's public
  description actually presupposes. The engines are not in it:
  no optimization engine, no workflow execution, no carrier
  integrations or carrier-side order execution, no line-level
  bill reconciliation against carrier feeds, no forecasting, no
  analytics or report-generation engine, no alert delivery, no
  portal web application. Each is named as an Extended gap in
  `UNION-SPEC.md` for the final batch.
- **The category's device surface is absent because the fork's
  description never claims it.** No enrollment, wipe, policy
  push, app management, or device registry exists in this build,
  and the gaps section of the union spec names that surface as
  category-level absences rather than letting the MDM label
  imply it. "Mobility" in the fork's prose means mobility
  telecom services in inventory, not managed handsets.
- Orders are records. Fulfilling one updates registry state
  inside this build only; no carrier is contacted and no money
  moves. Disbursement and carrier execution belong to the
  embedding organization's rails.
- Nothing in the build computes a score, a rating, an
  optimization, or a projection, and no record shape has a
  field for one — pinned by tests. A budget's projection is a
  caller-supplied value recorded verbatim.
- Budget availability is derived at read time and never
  stored; the stored budget record carries no obligated,
  spent, or available key — pinned by tests twice over.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization. Encryption is TLS
  when a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment (the fork's multi-tenant architecture
  is a property of its hosting platform).
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (16 evidenced claims from the
  single fork, taxonomy defined from its own description) or
  to the Moderate/L2 control families in `UNION-SPEC.md`.
  Counts are a floor, stated as such.
