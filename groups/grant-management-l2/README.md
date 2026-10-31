# Grant Management L2 — merged build (Operation DeadRamp, Phase 2, Group 45)

This is the merged, clean-room implementation of the **Grant
Management L2** singleton: **1 fork / vendor platform** from the
FedRAMP Marketplace (EY Grants Accelerator, Ernst & Young LLP),
built as one open-source service from the group's union contract
(`UNION-SPEC.md`). Grant Management is a brand-new category with no
parent group at any tier, so the function taxonomy was defined from
the fork's own marketplace description (the Group 1 method): **17
claims**, each carrying its source sentence as evidence.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 13 core functions

1. **Grant programs & membership** — programs (`gp-`) with title,
   opaque sponsor reference, an open window, and a budget in
   integer cents. Open status (`upcoming`/`open`/`closed`) is
   derived at read from the window, never stored.
2. **Applicant organization registry** — organizations (`org-`)
   known only by an opaque caller-supplied `ref` and a label; the
   record shape is pinned, so no field can hold a real identifier.
3. **Application records & lifecycle** — applications (`app-`)
   with requested amounts in integer cents and the lifecycle
   `draft → submitted → under_review → awarded / declined`
   (plus `withdrawn` from any open state).
4. **Review records** — a reviewer's own recommendation and note,
   recorded verbatim while an application is under review. Reviews
   are never aggregated and decide nothing by themselves.
5. **Decision & award records** — decisions (`dec-`) and, on
   approval, awards (`awd-`). The decider is never the submitter
   (separation of duties), and the **award-cap invariant** holds:
   awards against a program never exceed its budget. Rejection is
   whole — no partial records, no id consumed.
6. **Post-award report records** — report obligations (`rep-`) on
   awards with due dates; status (`pending`/`overdue`/`submitted`)
   is derived at read, never stored.
7. **Document & signature records** — document metadata and
   SHA-256 checksums (`doc-`) attached to programs, applications,
   or awards. No content is stored. A signature is a recorded
   event (who, when); the signing engine is not in this build.
8. **Form & workflow registries** — form definitions (`frm-`) and
   workflow definitions (`wfl-`) registered as data. The workflow
   registry **never executes** a definition; that is pinned by
   test.
9. **Communications records** — messages (`msg-`), notifications
   (`ntf-`, recorded, not delivered), and internal notes (`note-`)
   that stay internal: a read-only member cannot read them.
10. **Search & summary reporting** — substring search across
    programs, organizations, and application summaries; per-program
    summaries computed on read as counts and money sums. Never
    scores.
11. **REST API** — every function above over a JSON REST API.
12. **RBAC** — roles `admin`, `member`, `viewer` with a permission
    matrix enforced on every operation, layered with program
    membership.
13. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). All money is integer cents: floats, booleans, and
strings are rejected at the boundary.

## Run

```bash
cd groups/grant-management-l2
PYTHONPATH=src python3 -m grants serve            # http://127.0.0.1:8000
PYTHONPATH=src python3 -m grants serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m grants serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | member | programs, records, reviews, decisions (never on his own submissions) |
| `carol` | viewer | reads only, and never internal notes |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | read | `{"programs": [...], "organizations": [...], "applications": [...]}` |
| `GET /programs` · `POST /programs` | read / create_program | create → 201; `?now=` on reads |
| `GET /programs/{id}` | read | derived `status`, `awarded_cents`, `remaining_cents` |
| `POST /programs/{id}/members` | manage_members | body `{"username": ...}` |
| `GET /programs/{id}/summary` | read | counts and sums, computed on read |
| `GET /organizations` · `POST /organizations` | read / enter | create → 201 |
| `GET /organizations/{id}` · `POST /organizations/{id}` | read / enter | POST updates the label |
| `GET /programs/{id}/applications` · `POST` | read / enter | `?status=` filter; create → 201 |
| `GET /applications/{id}` | read | |
| `POST /applications/{id}/submit` · `/start-review` · `/withdraw` | enter / decide / enter | lifecycle transitions |
| `GET /applications/{id}/reviews` · `POST` | read / decide | record a review verbatim |
| `POST /applications/{id}/decide` | decide | body `{"approve": bool, "amount_cents": ..., "note": ...}`; never the submitter |
| `GET /applications/{id}/notes` · `POST` | enter | internal staff notes |
| `GET /applications/{id}/documents` · `POST` | read / record | metadata + checksum records |
| `GET /programs/{id}/awards` · `GET /awards/{id}` | read | |
| `GET /awards/{id}/reports` · `POST` | read / record | `?now=` on reads |
| `GET /awards/{id}/documents` · `POST` | read / record | |
| `GET /reports/{id}` · `POST /reports/{id}/submit` | read / record | |
| `GET /documents/{id}` · `POST /documents/{id}/sign` | read / record | sign records the signature event |
| `GET /programs/{id}/forms` · `POST` · `GET /forms/{id}` | read / record | form definitions as data |
| `GET /programs/{id}/workflows` · `POST` · `GET /workflows/{id}` | read / record | definitions only; never executed |
| `GET /programs/{id}/messages` · `POST` | read / record | `?org_id=` filter |
| `GET /programs/{id}/notifications` · `POST` | read / record | recorded, not delivered |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/grant-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 93 tests
```

**93 tests, all passing**, including the mutation-verified
negative control: removing the award-cap check from the real store
makes exactly 4 tests fail (see `tests/README.md` for the drill
record).

## Honesty

- The build implements the records substrate the fork's public
  description actually presupposes. The engines are not in it: no
  portal web application, no workflow execution, no form designer
  or rendering, no document storage, no e-signature signing
  engine, no payment execution, no delivery transport, no scoring
  or eligibility engine. Each is named as an Extended gap in
  `UNION-SPEC.md` for the final batch.
- The description claims **no money function and no scoring
  function**. Money appears only as fields on the records the
  claimed functions presuppose (requested amounts, program
  budgets, awarded amounts), under the integer-cents discipline,
  and that boundary decision is stated in the union spec rather
  than dressed up as a claim. Nothing in the build computes a
  score, a rating, or an eligibility determination, and no record
  shape has a field for one — pinned by tests.
- Statuses that depend on dates (program open status, report
  status) are derived at read time and never stored; the stored
  records carry no such key — pinned by tests.
- Awards are records. No money moves in this build; disbursement
  belongs to the embedding organization's payment rails.
- Demo identities are hooks, not an identity provider. IA-2 stays
  with the embedding organization. Encryption is TLS when a
  certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment.
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (17 evidenced claims from the single
  fork, taxonomy defined from its own description) or to the
  Moderate/L2 control families in `UNION-SPEC.md`. Counts are a
  floor, stated as such.
