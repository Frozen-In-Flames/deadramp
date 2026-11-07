# Final GAPS batch — Group 26 — Customer Service L1

Batch unit under `gaps-batch/DECISION.md`. The unit is the 10
**open** Extended entries of this group's GAPS.md section: 7
drafted `build-extension` and 3 drafted `stub-engine`. Disposition:
**7 built, 3 shipped as labeled reference implementations, 0
re-judged** — every entry carried under the drafted disposition,
in the forms the Customer Service L2 batch unit adjudicated for
this same package lineage (the two groups' `custsvc` cores are
byte-identical; `store.py` SHA-256 `05c749f3…` in both trees).

All extension code is one new module, `src/custsvc/extensions.py`
(`CustsvcExtensions`), wrapping the core `CustsvcStore`. The 7 core
modules are byte-identical to their pre-batch state (SHA-256
verified), and the founding test modules are untouched; the batch
adds `tests/test_gaps_batch.py`. Suite: **80 tests before, 126
after, all passing.**

## Tier discipline at L1 (what differs from the L2 unit)

The L2 forms were mirrored, not the L2 tier. Specifically:

- **No Moderate apparatus was imported.** The audit log this
  module writes to is this tier's plain append-only log — no
  hash-chain verification is called or claimed (the L1 founding
  spec states hash-chained audit is Moderate+ and out here).
  Extension mutations and denials land on that same log as
  `ext_*` / `ext_*:denied` actions, traceable to AU on the
  FedRAMP Low side of the crosswalk only, exactly as the founding
  spec frames it.
- **The role matrix is this group's.** Admin / agent / viewer;
  agents hold no `rule_write`, so SLA policy records and
  automation execution requests are admin-only here, checked
  through the core matrix before any state change — same
  operations-to-actions mapping as L2, enforced by *this* tier's
  matrix.
- **The GRC entry is claimed here, carried at L2.** At this tier
  the GRC claim is Riskuity's sole claim family (1 of the group's
  8 surviving claims). The entry text's "incl. compliance-
  framework support depth" lands as the same label-set records:
  the founding spec removed the `compliance_frameworks` raw hit as
  a wording artifact — the NIST/RMF/ATO sentence describes the
  vendor's experience, not a product function — and that removal
  stands. Registering a framework record named for a framework
  asserts no framework support, no assessment, and no compliance.
- Nothing in the unit raises the group's Low / LI-SaaS baseline,
  and the Zendesk addition's zero-claim, zero-core-delta posture
  is untouched.

## Per-entry dispositions

1. **Automation execution engines** — *built* (`built`). The
   founding doctrine is not repealed: the core rule registry
   never evaluates a condition and never executes an action,
   pinned by the founding suite. The entry lands in the L2 unit's
   adjudicated form: execution-*request* records against existing
   core rules (`request_rule_execution`: `exec-`, `executed_here:
   False`, `state: recorded_request_only`), verbatim execution
   *reports* (`record_execution_report`: `execr-`, reported
   outcomes only, `executed_here: False`), and an `execution_summary`
   derived at read. A test pins that a request changes neither the
   rule registry nor a case.
2. **GRC platform** — *built* (`built`). Framework records
   (`register_framework`: `fw-`, a label set), control records
   under a framework (`register_control`: `ctl-`, `control_ref`
   held as data), case-to-control mapping records
   (`map_case_to_control`: `cmap-`, both ends must exist), and
   `framework_posture` derived at read: control, mapping,
   mapped-case, per-status, and core-derived-breach **counts
   only** — no score is computed and nothing is stored on any
   record (the stored framework record's key set is pinned by
   test). See the tier note above on framework support: none is
   claimed.
3. **Knowledge base articles** — *built* (`built`). Article
   records with **append-only** revision records
   (`create_article` / `revise_article` / `list_article_revisions`:
   `kb-` / `kbrev-`). The stored article record holds exactly
   `{id, tags, created_by, created_utc}` (pinned by test); text
   lives only in revisions, each revision is a new record, no
   revision is ever edited or deleted, and the article view
   derives current title/body/revision count from the latest
   revision at read.
4. **Satisfaction / CSAT surveys** — *built* (`built`). Survey
   instruments (`create_survey`: `svy-`, `scale_max` an integer
   2..10 held as recorded terms; bool/float refused) and response
   records (`record_survey_response`: `svr-`) storing the rating
   **verbatim** and binding the respondent to a registered core
   requester by opaque ref (an unregistered ref is refused), so
   the pinned requester shape governs respondents too.
   `survey_tally` derives the count, the full-scale distribution,
   and the mean as an **exact rational** (`Fraction`, returned as
   numerator/denominator) at read; the stored survey record's key
   set is pinned — no tally or score key exists anywhere.
5. **SLA policy engine** — *built* (`built`). Policy records hold
   per-priority targets as data (`create_sla_policy`: `sla-`;
   unknown priority, zero/negative, float, and bool targets all
   refused at the boundary; admin-only under this tier's matrix).
   Breach is **derived at read** at the named seam
   `_is_breached_under_policy`: past creation + the recorded
   target for the case's priority; an uncovered priority or a
   terminal-status case is never breached. `sla_case_view`
   (covered flag, target, effective due instant, `derived: True`,
   `stored: False`) and `sla_breach_report` (evaluated/breached
   counts, overall and per priority) read the core case records
   and write nothing — a test pins that a policy view leaves the
   core case byte-identical (`due_at` stays `None`).
6. **Notification delivery & status-page hosting** — *built*
   (`built`). Delivery lands as `reference_transport` records,
   hosting as configuration over the core's already-derived
   public view — the forms the L2 unit adjudicated, with no
   delivery or hosting engine dressed up here. Notification
   records (`record_notification`: `ntf-`, `reference_transport:
   True`, `delivered_here: False`, `state:
   recorded_reference_only`; both the case and the recipient
   requester must exist) plus verbatim delivery reports
   (`record_delivery_report`: `ntr-`) and a derived-at-read
   `notification_summary` whose `delivered_here` stays False.
   Status-page records (`record_status_page`: `stp-`,
   `reference_stub: True`, `hosted_here: False`) and
   `status_page_view`, served from the core `public_status`
   derivation (`served_from: core_public_status_derivation`).
7. **Reporting / analytics engines beyond registry reporting** —
   *built* (`built`). `analytics_report`: deterministic counts
   over core records at read — cases by channel (None reported as
   `unspecified`), cases/breached per assignee (None as
   `unassigned`), breached by priority, distinct requesters with
   cases, alerts by severity, and alert linkage as an exact
   linked/unlinked/total count triple. **No float rate, ratio, or
   percentage is representable anywhere in the report**, and the
   report is a function of the records at the moment it is read
   (pinned by a two-read test; nothing is stored).
8. **Event detection, diagnosis & orchestration engines** —
   *labeled reference implementation* (`reference`). Detection-
   source registrations (`register_detection_source`: `det-`,
   `reference_stub: True`, `detects_here: False`) and verbatim
   orchestration-run records (`record_orchestration_run`: `orc-`,
   reported outcomes only, `executed_here: False`). A run may
   reference an alert that already exists in the core; a test
   pins that **a run creates no alert** — the core alert ingest
   remains the only alert path in this build.
9. **Real-time channels: live chat, voice / telephony** —
   *labeled reference implementation* (`reference`). Channel
   registrations (`register_channel`: `chn-`, kind one of
   `live_chat` / `voice` / `video` held as data, `media_here:
   False`) and session records against existing core cases
   (`record_channel_session`: `chs-`, `connected_here: False`,
   `state: recorded_report_only`). Nothing connects; no media
   exists in this build.
10. **AI assistance / deflection** — *labeled reference
    implementation* (`reference`). Assistant registrations
    (`register_assistant`: `ai-`, `inference_here: False`,
    `method: recorded_declaration_only`) and verbatim deflection
    reports (`record_deflection_report`: `air-`, reported
    outcomes only, `decided_here: False`). A test pins that a
    report of deflection leaves the reported case untouched
    (status still `new`); no model runs and no case is decided
    here.

## Cross-cutting pins (tests/test_gaps_batch.py)

- Extension operations map onto the core's fixed action set and
  are enforced before any state change or id allocation for
  User-like actors; denied attempts are recorded on the core
  audit log as `ext_<action>:denied` (agents cannot create SLA
  policies or execution requests — `rule_write` — and viewers
  cannot write anything; both pinned).
- Every successful extension mutation lands on the core audit log
  as an `ext_*` action; if the audit write raises, the record
  insertion and its id roll back before the error propagates
  (pinned: after a broken audit, the next framework is still
  `fw-1`).
- Creating every stub-family record plus an automation execution
  request changes no core record (case/alert/rule/requester/
  responder/schedule counts pinned before and after).
- Person-shaped refs resolve against the core's registered
  requesters only, so no extension record can smuggle an
  identifier the founding privacy shapes exclude.

## Fresh negative control

The batch's mutation-verified negative control is the SLA policy
breach derivation, in two layers (recorded in `tests/README.md`):

- `TestSlaNegativeControl.test_policy_breach_is_derived` runs in
  the suite: the canonical seam derives breach once the recorded
  target has passed; a `MutantCustsvcExtensions` whose
  `_is_breached_under_policy` is a no-op does not; treating the
  mutant's outcome as the expectation fails.
- The external drill: the real seam's final return was replaced
  with `return False` in `src/custsvc/extensions.py` (backup at
  `scratch/extensions.py.premutation`, SHA-256 at
  `scratch/extensions.py.sha256`, log at
  `scratch/gaps_mutation_run.txt`). The full suite then ran
  **FAILED (failures=3)** — exactly the three tests that depend on
  policy breach being derived (`test_breach_derived_from_recorded_terms`,
  `test_breach_report_counts`, `test_policy_breach_is_derived`) —
  and returned to **126 tests, OK** after restore (hash verified).

## Long tail (against this group's own function ranking)

| Family | Lands |
|---|---|
| Case / ticket registry, triage & lifecycle | Core (function 1) |
| Automated event detection, diagnosis & response | Core alert records (function 5); engines = entry 8 (reference) |
| Event orchestration, aggregation & alert prioritization | Core priority + alert records; orchestration = entry 8 (reference) |
| Automated actions & predefined workflows | Core rule registry (function 8); execution requests/reports = entry 1; execution itself not built |
| On-call scheduling & coverage | Core (function 6) |
| Responder assignment & mobilization | Core (function 3) |
| Status updates & status pages | Core derived view (function 7); delivery/hosting forms = entry 6 |
| GRC platform | Entry 2 |
| Compliance framework support (NIST / RMF / ATO) | Not claimed, and still not claimed: the founding spec removed the raw hit as a wording artifact; entry 2's framework records are operator label sets |
| Knowledge base | Entry 3 |
| CSAT surveys | Entry 4 |
| Real-time chat / voice channels | Entry 9 (reference) |
| AI assistance / deflection | Entry 10 (reference) |
| Reporting & dashboards | Core registry reporting (function 9) + entry 7 |
| Access control | Core (function 10) |
| Audit logging | Core (function 10); extension mutations and denials land on the same append-only log |

## Not covered

- **Execution itself**, in every family that names it: no rule
  runs, no orchestration performs, no notification is sent, no
  channel connects, no assistant answers or deflects. Those
  remain the work of executors and engines outside this build,
  whose outcomes this surface records verbatim as reported.
- The section's platform-layer lines (multi-tenancy architecture,
  encryption at rest / SC-28 in the UNION-SPEC's control table)
  are the platform-layer decision recorded in `PLATFORM-LAYER.md`
  at the repo root, not this unit.
- The Remainder Addition section's entry (proactive engagement &
  outreach tooling) is a different batch unit; nothing here
  touches it.
- Riskuity's GRC platform as a product: entry 2 is framework,
  control, and mapping records inside this substrate, not a build
  of Riskuity, and its claim remains its own. The same holds for
  PagerDuty's detection and orchestration engines under entry 8.
