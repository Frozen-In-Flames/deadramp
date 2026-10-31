# Talent Management L2

DeadRamp Phase 2, remainder unit `new-group:Talent Management|L2` — a
brand-new category group built from two FedRAMP Moderate (CMMC L2
planning-equivalent) offerings:

| Fork | Vendor | Product |
| --- | --- | --- |
| FR1831429369 | HireVue | Recruitment Assessments and Video Interviewing |
| FR2113557839 | Yello Dba Recsolu Inc | Yello Government Recruiting Solution |

This group is the candidate-facing **pre-hire acquisition surface**:
requisitions, pipelines, placements and stage movements, recruiting
events, assessments, interviews, and the counts that describe them.
Candidates are opaque references in an acquisition pipeline, never
personnel records.

**Boundary.** Human Resources L2 (Group 21) is the personnel system of
record — positions, personnel actions, onboarding. Nothing from that
group is imported here. The moment a hire becomes a personnel action,
it belongs to HR's substrate, not this one. The untiered Talent
Management / Talent Development census sets are different units and
were not imported either. The full boundary statement, counting
method, and function ranking are in [UNION-SPEC.md](UNION-SPEC.md);
the per-fork spec sheets are in [specs/specs.json](specs/specs.json).

FedRAMP authorizes products; CMMC certifies organizations. The L2
tier here is a planning equivalence, never a credential claim.

## Core functions (13)

1. Organization registry & membership (the tenancy boundary)
2. Candidate registry (opaque references only)
3. Requisition records (open/closed lifecycle; `past_close` derived)
4. Pipeline definitions (ordered stage lists, recorded verbatim)
5. Candidate placements & stage movements (bounds-checked; current stage derived)
6. Recruitment event records (in-person / virtual kinds)
7. Event registration records (registration and check-in)
8. Assessment records (verbatim outcome labels; no scores)
9. Interview records (video / in-person metadata; no media)
10. Workflow definition registry (records only; never executes)
11. Registry reporting (counts only; no scores, ratios, or ROI)
12. Registry search (literal substring, membership-scoped)
13. Access control & audit (RBAC hooks; append-only log; denials recorded at the HTTP layer)

The group's signature invariant is the **stage bounds rule**: a
movement's `stage_index` must satisfy
`0 <= stage_index < len(stages)`, enforced before anything is
stored, so a placement's derived current stage always names a real
stage. It is mutation-verified — see [tests/README.md](tests/README.md).

## Run

```
cd groups/talent-management-l2
PYTHONPATH=src python3 -m talentmgmt serve --port 8817
```

Demo users (hooks for the embedding organization's IdP, not an IdP):

| User | Role | Can do |
| --- | --- | --- |
| alice | admin | everything, including reading the audit log |
| bob | member | all registry writes and reads except creating organizations and reading the audit log |
| carol | viewer | read organizations and reports |
| dave | member | authenticated, but a member of no organization (outsider scoping demo) |

Authenticate with `X-User` / `X-Role` headers matching the registry.

## Endpoints

| Route | What |
| --- | --- |
| `GET /health` | liveness, no auth |
| `POST /organizations`, `GET /organizations`, `GET /organizations/{id}` | organization records |
| `POST /organizations/{id}/members` | add a member (admin) |
| `GET/POST /organizations/{id}/candidates` | opaque candidate registry |
| `GET/POST /organizations/{id}/requisitions` | requisitions |
| `POST /organizations/{id}/requisitions/{rid}/close` | close a requisition |
| `GET/POST /organizations/{id}/pipelines` | pipelines with stage lists |
| `POST /organizations/{id}/pipelines/{pid}/placements` | place a candidate |
| `GET /organizations/{id}/placements`, `GET /organizations/{id}/placements/{pid}` | placements with derived current stage |
| `POST /organizations/{id}/placements/{pid}/movements` | record a stage movement (bounds-checked) |
| `POST /organizations/{id}/placements/{pid}/withdraw` | withdraw a placement |
| `GET/POST /organizations/{id}/events` | recruiting events |
| `POST /organizations/{id}/events/{eid}/registrations` | register a candidate |
| `POST /organizations/{id}/registrations/{rid}/check-in` | check in a registration |
| `POST /organizations/{id}/events/{eid}/complete` · `/cancel` | event lifecycle |
| `GET/POST /organizations/{id}/assessments` | assessment records |
| `POST /organizations/{id}/assessments/{aid}/complete` | complete with a verbatim outcome label |
| `GET/POST /organizations/{id}/interviews` | interview records |
| `POST /organizations/{id}/interviews/{iid}/complete` · `/cancel` | interview lifecycle |
| `GET/POST /organizations/{id}/workflows` | workflow definitions (records only) |
| `GET /organizations/{id}/report` | the 18-key counts report |
| `GET /search?q=...` | membership-scoped registry search |
| `GET /audit` | audit entries (admin only; the read is itself audited) |

## Permission matrix

| Action | admin | member | viewer |
| --- | :---: | :---: | :---: |
| org_read | ✓ | ✓ | ✓ |
| org_write | ✓ | | |
| candidate_write | ✓ | ✓ | |
| requisition_write | ✓ | ✓ | |
| pipeline_write | ✓ | ✓ | |
| event_write | ✓ | ✓ | |
| assessment_write | ✓ | ✓ | |
| interview_write | ✓ | ✓ | |
| registry_write | ✓ | ✓ | |
| report_read | ✓ | ✓ | ✓ |
| audit_read | ✓ | | |

Organization membership is a second boundary enforced by the store on
top of this matrix: a platform role alone never grants access to an
organization's records.

## Control mapping (summary)

The core answers the NIST 800-53 Moderate baseline through the house
pattern: AC (RBAC matrix + membership scoping), IA (identity supplied
by the embedding organization; demo users are hooks, IA-2 stays with
that organization), AU (append-only audit, denials recorded), SI-10
(boundary validation, including the stage bounds rule), SC-8
(transmission protection is the deployment's responsibility). The full
traceability table is in UNION-SPEC.md. None of this is a fork claim:
the forks claim acquisition functions, and the baseline is what a
Moderate deployment of those functions must answer.

## Tests

99 tests, all passing, including a mutation-verified negative control
(the stage bounds drill fails exactly 5 tests with the seam removed).
Details: [tests/README.md](tests/README.md). Live smoke:
`PYTHONPATH=src python3 tests/smoke.py` prints `SMOKE OK`.

## Honesty: what this group does not do

The spec registers eight gaps, each an engine the descriptions point
at but a records core cannot honestly ship:

1. **Video interview platform** — media capture, streaming, playback.
2. **Assessment delivery & scoring engines** — instruments are
   delivered and scored elsewhere; this core stores a verbatim
   outcome label and no score field exists anywhere.
3. **Predictive I-O models & AI** — HireVue's validated science is a
   model, not a record.
4. **Virtual event platform** — the media channel behind virtual
   events; event records note the kind only.
5. **Pipeline automation engine** — workflow definitions are
   registered; nothing executes them (pinned by test).
6. **Analytics & visualization engines** — including ROI
   determination; the report is counts only.
7. **Talent development programs** — post-hire development content
   and delivery.
8. **Identity provider / candidate identity verification** — identity
   belongs to the embedding organization.

Two deliberate absences, stated in the spec: there is **no
communications surface** (no email, messaging, or campaign records)
and **no integration registry**, because neither fork's description
claims them. "Diverse" in Yello's description is an adjective on
pipelines, not a diversity-analytics function, and no such function
was built.
