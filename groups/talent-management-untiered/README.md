# Talent Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Talent
Management — census unit `untiered:Talent Management` in
`../../remainder.json`, Untiered Set 21. **This is an untiered
set, and that means something specific:** every member's FedRAMP
impact level is **Unknown** in the source dataset. The source
publishes no baseline for these offerings, so **tier stays
null**: no tier is assigned, no CMMC equivalence is drawn, and
this build asserts **no control baseline**. Per PIPELINE.md,
untiered offerings "build to their documented control claims;
tier stays null in the registry until the source publishes a
baseline." The union contract is [`UNION-SPEC.md`](UNION-SPEC.md);
per-fork spec sheets are in [`specs/specs.json`](specs/specs.json),
each recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests.

Talent Management is the category founded by Remainder Group 3
(`../talent-management-l2/`): the candidate-facing pre-hire
acquisition surface. It is a different category from Talent
Development (Untiered Set 20), Learning Management, and Human
Resources, and nothing was borrowed from any of them.

The 2 forks were spec'd under the category's existing 12-family
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding Talent Management L2
group's original shipped claim tables exactly — **2 of 2 forks,
14 of 14 claims, deep-equal** — before tagging this set. Result
here: **0 claims across the set; both forks are zero-claim.** No
family's phrase occurs in either description (a case-insensitive
re-check also produces no hits). The substance both descriptions
assert in other words is itemized in the union spec's Named
absences and registered as gaps — not hidden, and not repaired
by re-tuning the taxonomy.

The build implements the category's **thirteen-function
substrate** — the candidate-acquisition records machinery the
founding group's forks presuppose — carried from the founding
Talent Management L2 build (`../talent-management-l2/src/
talentmgmt/`): 5 of 7 modules byte-identical, the other two
(`__init__.py`, `store.py`) differing by docstring only, where
the founding text named the L2 group and this tree names tier
null (SHA-256 accounting below). **No core function is
claim-supported in this set** — every function is **carried, not
claimed**.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2635930425 | CodeSignal, Inc. | CodeSignal | 0 |
| FR2631747327 | Geographic Solutions Inc. | VOS Sapphire | 0 |

Both are Initial Implementation / SaaS in the source. In
`forks.json`, CodeSignal is filed "Human Resources" (source
business categories: Human Resources, Talent Management, Talent
Development, Education & Training, Artificial Intelligence (AI))
and VOS Sapphire is filed "Uncategorized (none in source)" with
no source business categories; the census assigned both to
Talent Management from their own descriptions, and the sheets
record the assignment and the filed values as-is. Authorization
statuses are record data, not claims.

## The 13 core functions

1. **Organization registry & membership** — the tenancy boundary.
2. **Candidate registry** — opaque references only; no field can
   hold a real person's name, contact detail, or identifier.
3. **Requisition records** — open/closed lifecycle; `past_close`
   derived at read, never stored.
4. **Pipeline definitions** — ordered stage lists, recorded
   verbatim.
5. **Candidate placements & stage movements** — bounds-checked by
   the **stage bounds rule** (`0 <= stage_index < len(stages)`,
   the category's signature invariant); current stage derived at
   read, never stored.
6. **Recruitment event records** — `in_person` / `virtual` kinds.
7. **Event registration records** — registration and check-in.
8. **Assessment records** — verbatim caller-supplied outcome
   labels; **no score field exists anywhere**.
9. **Interview records** — `video` / `in_person` metadata; no
   media, no transcript, no notes field.
10. **Workflow definition registry** — records only; never
    executes (pinned by test).
11. **Registry reporting** — counts only; no scores, ratios, or
    ROI.
12. **Registry search** — literal substring, membership-scoped.
13. **Access control & audit** — RBAC hooks layered with
    organization membership; append-only log; denials recorded
    at the HTTP layer.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `org-`, `can-`,
`req-`, `pip-`, `plc-`, `mov-`, `evt-`, `reg-`, `asm-`, `int-`,
`wfl-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m talentmgmt serve --port 8817
```

Options: `--host`, `--audit-log PATH` (JSONL audit persistence),
and `--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User | Role | Can do |
| --- | --- | --- |
| alice | admin | everything, including reading the audit log |
| bob | member | all registry writes and reads except creating organizations and reading the audit log |
| carol | viewer | read organizations and reports |
| dave | member | authenticated, but a member of no organization (outsider scoping demo) |

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

Organization membership is a second boundary enforced by the
store on top of this matrix: a platform role alone never grants
access to an organization's records. A permitted role performing
a forbidden action gets 403; validation failures get 400; unknown
objects get 404. Errors are always JSON `{"error": "..."}` and no
stack trace is ever returned to a client.

## API endpoints

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

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**102 tests, OK** at delivery: the founding group's 92-test core
suite carried with the code, plus 10 spec tests pinning this set
(exactly 2 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; descriptions
byte-equal to the cache and the census; the literal claim table
of 0 claims with both forks zero-claim; census citations 4/4;
certified_services never matched). The category's signature
stage-bounds mutation drill was re-run in this tree — exactly 5
failures under the mutant, store restored and SHA-256 verified
(see `tests/README.md`). Live smoke:
`PYTHONPATH=src python3 tests/smoke.py` prints `SMOKE OK`.

## Byte-identity accounting

`src/talentmgmt/` is carried from the founding group
`../talent-management-l2/src/talentmgmt/` — **5 of 7 modules
byte-identical**; `__init__.py` and `store.py` differ by their
docstrings only (the founding text named the L2 group; this tree
names tier null — no code differs):

| Module | SHA-256 (this tree) | vs founding |
|---|---|---|
| `__init__.py` | `ba4365ecb0aaefe38c050d7a017b32846b77936c76507280f686d1797cf2df57` | docstring only |
| `__main__.py` | `3b563d9e10a640d079eeee1baf11f4331582617f8b62ded361a0d8bf7cdccf52` | identical |
| `access.py` | `412feb21a0e7c4a9912e898c9be518ad50ab7db5d44a1add667539a1833df52d` | identical |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` | identical |
| `errors.py` | `1116e1f42d6ae728e2d8be379523825573d02ea57d871bf53b5ef82b5e90d7a1` | identical |
| `service.py` | `a6acbaaae3ac88cb1396d3dc68efcbbb2d22ba9b20ac76496eeca41f0acd97e8` | identical |
| `store.py` | `ff0cab40ba3b90c226a9cf993780dc26bc3dec8556d072c3bc664f5c832b08af` | docstring only |

The test suite is likewise carried (the founding suite minus its
`test_specs.py`, which pins the founding census unit), with one
labeling fix in `tests/talentmgmt_helpers.py` (its docstring now
names this untiered set instead of L2) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

**Taxonomy tier — none.** No taxonomy family fires in this set,
and the category's taxonomy is functional by founding design.

Documented at **prose weight** by one fork in the set:

- **Identification & authentication (IA) — in part** —
  CodeSignal (FR2635930425): its description states the offering
  provides "identity" among the support services for its
  assessments and interviews, and that its proctoring and
  integrity services handle government-issued identity documents
  and session video. **No mechanism is named** — no SSO, MFA, or
  federation is asserted in its `service_desc`, and none is
  documented here. (An "SSO (SAML) and SCIM Provisioning" entry
  exists in the record's `certified_services` field; that field
  is never matched and documents nothing in this build.)

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AC (CodeSignal's "Tenant data
is logically segregated" is multi-tenancy platform prose, not an
access-control claim), AU (no audit language occurs; "reporting"
is a function noun), CA (VOS Sapphire's "improves collaboration
and compliance" is outcome prose naming no control), and SC (no
encryption language occurs anywhere in the set) — is asserted by
no description in the set. If the source later publishes an
impact level for either of these offerings, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented
  control language is recorded as *its* claim, never as the
  build's control attainment.
- **Zero claims, plainly.** Both forks are zero-claim under the
  category's verbatim taxonomy. Their described substance —
  CodeSignal's pre-hire assessments, live and AI-conducted
  interviews, proctoring, and technical learning; VOS Sapphire's
  labor exchange, case management, employer services, and
  unemployment insurance platform — is registered as gaps in its
  own names (16 gaps in `UNION-SPEC.md`: the founding group's 8
  engine gaps restated at 0 claimants, plus 8 from this set's own
  descriptions). Nothing was back-filled to make the set look
  complete.
- **No score is computed anywhere in this category.** The
  doctrine is the founding group's, preserved exactly:
  assessment records store a caller-supplied outcome label
  verbatim, no record shape carries a score, rating, ranking, or
  match, and reporting is counts only. Neither untiered
  description tests the doctrine ("score" occurs in neither
  `service_desc`; it occurs only inside CodeSignal's
  `certified_services`, never matched).
- **Extended functions are specified, not implemented.** NOT
  implemented: the video interview platform; assessment delivery
  & scoring engines; predictive I-O models & AI; the virtual
  event platform; the pipeline automation engine; analytics &
  visualization engines; talent development programs; the
  identity provider / candidate identity verification service;
  assessment proctoring & integrity services; the experiential
  technical learning platform; the integration & API services
  layer; and VOS Sapphire's labor exchange, workforce case
  management, employer services, unemployment insurance, and
  labor market information platforms.
- **The build stores no PII — a fork here does.** CodeSignal's
  description states its offering handles candidate PII (name,
  email address, IP address) and, for proctoring,
  government-issued identity documents and session video. That
  is the fork's data practice, recorded on its sheet. This
  substrate holds opaque candidate references only: no field
  exists that could hold a name, contact detail, identity
  document, resume, assessment content, or interview recording.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  `carol`, and `dave` are documented demo identities supplied by
  header; the service enforces the role permission matrix and
  organization membership on those hooks and ships no identity
  provider, no credential store, and no authentication of its
  own.
- **Named absences stand.** All twelve taxonomy families have 0
  claimants in this set. The taxonomy was not re-tuned, and no
  substance was approximated into a family it does not name.
