# Final GAPS batch — Remainder Singleton 65, Storage L3-adjacent

Date: 2026-11-07. This singleton's section of `../../GAPS.md`
listed 7 open entries (inventory idx 735–741); all 7 are
closed by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/storage/extensions.py`
(`StorageExtensions`, wrapping the core `StorageStore`; all
seven core modules byte-identical, SHA-256 verified against
the pre-build baseline — store.py still `903dd5d2…`, audit.py
still `bb272265…`), and `tests/test_gaps_batch.py` (34 tests).
Full suite: **127 → 161 tests**, all passing.

The singleton's situation shapes every landing form below.
This fork (Commvault Cloud for Government) claims **zero** of
the category's 11 taxonomy families; the entire core is
carried substrate from the Storage L2 union, flagged
carried-not-claimed, and the 7 gaps are this fork's own
substance — a backup and recovery service's engines. Those
engines run over protected workloads and payloads that this
substrate structurally does not hold (the founding
core-boundary decision is "metadata, never payloads"), so
each entry lands as its records form over the carried core:
job, condition, outcome, and receipt records, with every
current state derived at read and the execution half stated
absent on the record itself. The Moderate-tier forms in
`groups/storage-l2/BATCH.md` were read where the families
overlap (reported outcomes, gated decisions, derived views)
and adapted to this tier's baseline; none of the L2 module's
shapes were copied unchanged, because this fork's gaps are a
different fork's substance, not the parent's.

The High apparatus binds the extension surface exactly as it
binds the core: extension audit actions land on the core's
hash-chained, fail-closed log; denied write attempts are
recorded with a `:denied` suffix before the error propagates;
and the separated `auditor` role — which holds `audit_read`
and nothing else — is denied every extension operation, reads
included (pinned by test; its audit-review duty stays
available through the core's `audit_read`). PLATFORM-LAYER.md
decisions cited per entry: decision 1 (connectors authenticate
no one), decision 4 (disposition and retention enforcement is
the embedding organization's records schedule — backup
schedules and outcomes here are records, never enforcement),
and decision 6 (hosting and console surfaces are deployment
properties unless a group's spec claims a records function for
them — this fork's spec names its Command Center console, so
the console's records form lands as a build entry below).

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 735 | Backup & recovery engine: the fork's headline function (it retires the category's backup absence in substance on this fork's own words; it produces no claim, because the taxonomy is the founding fork's archive vocabulary) | reference | Backup job records (`bak-`; action: archive) bound to a core collection and a registered integration: schedule label plus item/byte counts stored **as reported**. Backup outcome records (`bout-`) and recovery report records (`rcv-`) hold `reported_*` labels verbatim; `backup_job_view` derives both current labels and both counts at read through the shared `_latest_label` derivation, stored nowhere. Every record carries `reference_stub: True` (outcomes/reports also state `backed_up_here` / `recovered_here: False`; jobs also carry `reference_transport: True`). Recording a job creates or changes no core record (pinned). |
| 736 | Anomaly detection & alerting engine | reference | Anomaly report records (`anm-`; action: discover): detector label, anomaly count, and severity label stored **as reported** by the external detector, `reference_stub: True`, `detected_here: False`. Alert dispatch receipts (`alr-`) carry `reference_stub: True` and `reference_transport: True`, `alerted_here: False`; `anomaly_report_view` derives `dispatch_count` at read. Detection is inference over protected data this substrate does not hold; only its reports land here. |
| 737 | Granular data remediation engine | built | Remediation action records (`rem-`; action: enforce) over core messages: an action from this module's remediation vocabulary (`quarantine_copy` / `remove_copy` / `revoke_access` / `restore_copy`) under a stated policy reference, `executed_here: False`, no `reference_stub` key. Recording is **gated by the fresh negative control's seam** (below): the message's derived retention state at the action moment comes from the core's seam, and an action for a `disposed` message is refused whole. Recording an action changes no core record (pinned: message view and core enforcement list byte-identical before/after). `remediation_action_view` derives the current state and current actionability at read. The records substrate genuinely carries this entry — a decision record over the archive's own messages, gated by the archive's own derivation — so it closes `built` in the same form the L2 unit's enforcement-decision entry (idx 732) closed `built`. |
| 738 | Workload protection connectors | reference | Workload connector records (`wlc-`; action: register) naming the protected workload and the connector by labels — the fork's catalogue names held as data — `reference_stub: True`, `connected_here: False`, `protected_here: False`. Coverage records (`cov-`) hold protected-item counts **as reported**, with `reference_transport: True`; `workload_connector_view` derives `coverage_count` at read. Recording one opens no connection and authenticates no one (PLATFORM-LAYER.md decision 1). |
| 739 | Management console (the fork's command-center surface) | built | Console panel definition records (`pan-`; action: admin — console configuration is the administrative plane, and an operator's attempt is refused and audited `:denied`, pinned): panel label, scope label, and widget labels held **as data**, `rendered_here: False`, no `reference_stub` key. `console_view` is the surface's derived form: the core summary carried whole (through the core's own seam) plus this module's extension counts and panel count, computed at read and stored nowhere. Nothing is rendered, served, or operated — the records function the fork's spec names for its console, per PLATFORM-LAYER.md decision 6 (see the near-the-line statement below). |
| 740 | SaaS operations automation | built | Automation rule definition records (`aut-`; action: admin): rule, trigger, and action labels held **as data**, `executed_here: False`, `operated_here: False`, no `reference_stub` key — definitions are held, never run (the house registry rule). Automation run records (`run-`; action: register) hold `reported_*` outcome labels verbatim with `executed_here: False`; `automation_rule_view` derives `run_count` and the current outcome label at read. The vendor's operation of its own service is never performed here; only its definitions and its reported runs land. |
| 741 | Hybrid cloud synchronization engine | built | Sync condition records (`hsc-`; action: archive) bound to a core collection and a registered integration: the condition named by an opaque label, `synchronized_here: False`, no `reference_stub` key. Sync outcome records (`sout-`) hold the outcome label and object count **as reported** by the external engine; `sync_condition_view` derives the outcome count, the current outcome label, and the latest reported object count at read. Recording conditions or outcomes changes no core record (pinned). Peers and estate sides are records (the integration record and its label), never live endpoints; nothing is moved or reconciled in this process. See the near-the-line statement below. |

Closure tokens: 4 entries close as `built` (737, 739, 740,
741) and 3 as `reference` (735, 736, 738) — exactly the
drafted triage split; **no entry was re-judged**.

## Fresh negative control

The batch's fresh mutation-verified negative control is the
remediation-eligibility seam,
`StorageExtensions._derive_remediation_eligibility` in
`src/storage/extensions.py`: a remediation action for a
message whose derived retention state is `disposed` must be
refused whole (nothing stored, no id consumed), because once
disposition is recorded there is nothing left in this
substrate for a data-level action to concern. Verified two
ways (full record in `tests/README.md`):

1. **In-suite mutant**
   (`TestRemediationEligibilityNegativeControl`): the
   canonical refusal is asserted on the real implementation; a
   mutant subclass whose seam reports every state eligible
   waves the same action through; the canonical expectation
   therefore fails against the mutant.
2. **External drill**: the seam's comparison in the real file
   was patched to `return True`, the full suite re-run —
   **exactly 2 failures out of 161**, both in the batch's own
   new tests
   (`TestRemediationActions.test_view_derives_current_state`,
   `TestRemediationEligibilityNegativeControl.test_canonical_refusal_on_the_real_extension`);
   all 127 pre-existing core tests still passed. The file was
   restored from `scratch/extensions.py.premutation`, verified
   byte-identical by SHA-256 (`44f1c5b5…`), and the suite
   re-ran green.

## Near-the-line statements (stated plainly, not re-judged)

- **Synchronization (741)** closes `built` as condition +
  reported-outcome records, in the same posture as the L2
  unit's disposition-outcome entry (idx 734, closed `built`
  there): the substrate carries the condition the engine
  maintains and the engine's own reports of maintaining it,
  with `synchronized_here: False` on every record. What does
  not land is any data movement or reconciliation — there is
  no payload here to synchronize and no live peer to
  synchronize with. The parent may re-token this entry
  `reference` if it judges the condition/report form
  insufficient; the build form would not change.
- **Console (739)** closes `built` as panel definitions plus
  a derived view. PLATFORM-LAYER.md decision 6 keeps console
  surfaces at the deployment layer *unless* a group's spec
  claims a records function for them; this fork's spec names
  the Command Center as its operator interface over
  protection, monitoring, and reports, and the records form of
  exactly that — what panels exist, over what scope, showing
  which recorded counts — is what was built, labeled
  `rendered_here: False`. No interface is served or rendered.
- **Backup & recovery (735)** stays `reference` although its
  records are as concrete as 741's, because the drafted
  disposition and the substance agree: the engine's work *is*
  moving and restoring payload bytes, and there are no bytes
  here. Its job/outcome/recovery records are the reference
  landing form, labeled as such on every record.

## Not covered

- No HTTP surface was added for the extension records (the
  sibling batch units' store-level pattern); the core REST API
  is untouched.
- No payload byte, protected-workload datum, key material, or
  message content exists anywhere in this unit — by design,
  and pinned by the tests above (exact key sets per record
  type, the recursive forbidden-key scan over every record and
  view, and `TypeError` on smuggled `content=` / `payload=` /
  `key_material=` keywords).
- The five High baseline gaps (MFA & authenticator management,
  FIPS-validated cryptography, encryption at rest, audit
  retention, session lock/termination) stay as recorded in the
  union spec; PLATFORM-LAYER.md carries their written
  dispositions, and nothing in this unit re-opens them.
