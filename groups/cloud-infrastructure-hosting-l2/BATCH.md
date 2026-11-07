# Final GAPS batch — Remainder Group 4, Cloud Infrastructure & Hosting L2

Unit: the 14 open entries of the "Remainder Group 4 — Cloud
Infrastructure & Hosting L2 (6 forks)" section of the repo GAPS.md
(inventory idx 976–990, excluding idx 982, already closed
`re-scoped` under PLATFORM-LAYER.md decision 1 — untouched here).

Built 2026-11-07 under gaps-batch/DECISION.md. Extension code is
one new module, `src/cloudinfra/extensions.py`
(`CloudInfraExtensions`, a wrapper over the core store); **all
core modules are byte-identical** — no core change was needed, so
none was made. Tests: `tests/test_gaps_batch.py` (32 tests); full
suite 118 → 150, all green on the final tree. Nothing here
provisions, orchestrates, executes, collects telemetry, carries
traffic, backs anything up, performs cryptography, or verifies
anything against an external source: the build remains a records
substrate *about* hosting, never a host (PLATFORM-LAYER.md
decision 6).

## Per-entry dispositions

### Built (build-extension, 6)

1. **Template execution engine** (idx 978) — *Built in the only
   form the entry's own text allows.* The registry stores settings
   verbatim and never executes, so the extension records
   **deployment-intent records** referencing a core template, a
   tenancy, and a workload (optional environment/deployment links,
   all validated through the core API). The template's
   `settings_text` is derived into the read view from the core
   template at read time and is never copied onto the stored
   intent (pinned); intents carry `executed: False` and a guarded
   recorded → cancelled lifecycle; a test pins that no execute /
   apply / launch / run operation exists on the extension class.
2. **Platform security service engines** (idx 980) — *Built as
   records.* **Security-service configuration records** (settings
   stored verbatim against a core security service record) plus
   **reported check-result records** whose outcome vocabulary is
   report-shaped by construction (`reported_pass` /
   `reported_fail` / `reported_inconclusive`) — the engines ran
   elsewhere; this build runs no check. A per-service summary
   (counts by outcome, latest outcome) is derived at read.
3. **Operations execution engines** (idx 984) — *Built as
   records.* **Operation request records** in the core's
   operations-kind vocabulary, optionally linked to a core
   operations task, with recorded states
   (requested → reported_completed / reported_failed / cancelled)
   and `executed: False` throughout. Outcomes are recorded as
   reported by the executing system; nothing executes here.
4. **Invoicing / billing & FinOps engine** (idx 985) — *Built as
   records with no money shape, as the entry's own text binds.*
   **Invoice records**: opaque reference, core account link,
   YYYY-MM period, optional label, recorded status with a guarded
   issued → settled / void lifecycle, one invoice per account per
   period (mirroring the core's utilization discipline). The
   record denominates nothing — no amount, rate, fee, or unit
   field exists on it (exact key set pinned). The **FinOps
   summary** is derived at read from the core's account and
   utilization records plus the invoice records: account counts,
   integer service-unit sums by period, invoice counts. A
   recursive key scan over every extension record and summary
   pins the absence of any money-shaped key.
5. **Application resource management engine** (idx 987) — *Built
   as records.* **Resource allocation records** over opaque
   targets in integer service units (compute / memory / storage /
   network; booleans, floats, strings, and negatives rejected at
   the boundary, mirroring the core's utilization discipline),
   optionally linked to a core deployment, with a guarded
   active → released lifecycle. Utilization counts and active-unit
   sums are derived at read — no scheduler runs.
6. **Residency & personnel verification** (idx 990) — *Built as
   records.* **Verification case records** over opaque subject
   references (data residency / personnel U.S. citizenship /
   operations residency; optional core environment link) plus
   **outcome records reported by the embedding organization's
   verification process**, stored verbatim as reported. Nothing
   is verified against any external source. The case's status and
   current outcome are derived at read from its outcome records
   and never stored (pinned). Outcomes are guarded by the batch's
   fresh separation-of-duties seam,
   `_check_verification_decider_not_opener`: the outcome recorder
   is never the case opener (denials audited with
   `ext_verification_outcome:denied`).

### Labeled reference implementations (stub-engine, 8)

Every record below carries `reference_stub: True` and status
`recorded_reference_only`; creating one changes no core record
(pinned against the core `org_report`).

7. **Hosting platform / provisioning & orchestration engines**
   (idx 976) — provisioning-plan reference records
   (`provisioned: False`). The platform layer entire stays a
   deployment property (PLATFORM-LAYER.md decision 6).
8. **Elastic Stack hosting engine** (idx 977) — hosted-deployment
   reference records with the delivery form recorded as a label
   (`hosted` / `serverless`, the fork's own forms)
   (`hosted_here: False`).
9. **Monitoring & observability engines** (idx 979) —
   telemetry-pipeline reference records, optionally linked to a
   core monitor record, carrying `reference_transport: True` and
   `telemetry_collected: False`: the reference collects nothing
   and moves nothing.
10. **Backup execution & disaster-recovery orchestration**
    (idx 981) — execution reference records in the core's
    protection-kind vocabulary, optionally linked to a core
    protection record (`executed: False`).
11. **Encryption implementation & key management** (idx 983) —
    key and certificate **metadata records only** (kind, label,
    caller-stated algorithm label, note), pinned to an exact key
    set; there is no parameter that can carry key material and no
    field that can hold it. Per PLATFORM-LAYER.md decisions 2–3:
    no cryptography is performed and no FIPS-validated module is
    claimed; the build's encryption surface remains caller-stated
    labels, exactly as in the core.
12. **AI recommendation engine** (idx 986) — engine reference
    records (`issues_recommendations: False`); recommendations
    the engine issues are recorded by the core's existing
    recommendation records, and this reference generates none.
13. **CDN operation** (idx 988) — delivery reference records
    carrying `reference_transport: True` and
    `traffic_carried: False`.
14. **Assessment & Authorization support services** (idx 989) —
    support-engagement reference records
    (`package_prepared: False`); recording one prepares no
    authorization package and asserts no authorization.

## Re-judgments

None. All 14 entries fit their drafted dispositions on a close
reading of the group's UNION-SPEC: the six build-extension entries
land in the records/derivation forms above (two of them — template
execution and invoicing — in exactly the bounded forms their own
entry texts state), and the eight stub-engine entries ship as
labeled reference implementations.

## Verification record

- Full suite: 118 tests before, **150 after, all passing**
  (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Fresh mutation-verified negative control: the
  `_check_verification_decider_not_opener` seam (in-suite mutant
  in `tests/test_gaps_batch.py`, plus a recorded file-level drill
  — seam condition replaced with `if False:`, full suite re-run,
  **exactly 2 failures**, both verification-guard tests; file
  restored byte-identical, SHA-256 verified, suite re-verified
  green). Recorded in `tests/README.md`.
- Core smoke still passes (`tests/smoke.py` prints `SMOKE OK`);
  core modules untouched.
