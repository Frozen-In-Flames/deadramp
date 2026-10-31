# Cloud Infrastructure & Hosting L2 — tests

Stdlib `unittest` only. Every test docstring names the core
function or spec property it pins. 118 tests.

## Run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 118 tests
PYTHONPATH=src python3 tests/smoke.py                       # live smoke
```

## Map

| Module | Pins |
|---|---|
| `test_organizations.py` | Core 1/16: org registry, duplicate refs consume no id, creator-or-admin member gate, membership-scoped listing, role enforcement for User actors, string actors carry identity only, mutations audited |
| `test_tenancies_environments.py` | Core 2/3/4: hosting-model vocabulary, provider links validated in-org, derived deployment counts (never stored), environment lifecycle guards, residency label |
| `test_deployments.py` | Core 5: link validation, lifecycle guards, and the functional slot-rule cases (per-tenancy, per-workload, frees after stop, refused activation changes nothing) |
| `test_records.py` | Core 6/7/8/9/10: template settings verbatim + no execute/apply/launch/provision operation exists anywhere on the store; kind vocabularies for monitors, security services, protection records, identity configs; identity config exact key set (no credential field) |
| `test_operations.py` | Core 11/12/13: derived `overdue` at read (never stored), task lifecycle, account lifecycle, utilization integer-units discipline (float/bool/string/negative rejected), period format, one record per account-period, closed accounts refuse utilization, recommendation kinds |
| `test_reports_search.py` | Core 14/15: report counts and unit sums, overdue count derived with `at`, recursive key scan (no score/money keys anywhere in a report), membership-scoped search |
| `test_access_audit.py` | Substrate: role ladder facts (admin 11 actions; member lacks org_write/audit_read; viewer read-only), require() validation, audit copy-on-read, JSONL persistence round-trip |
| `test_privacy.py` | Privacy discipline: recursive field-name scan across every entity view and the report (no credential/content/identifier field), derived values absent from stored records, no store signature accepts a content/credential parameter |
| `test_service.py` | HTTP layer: health, 401 on missing/mismatched auth, end-to-end flow incl. the slot refusal as 400, viewer write 403, 404, validation 400, audit endpoint admin-only with `:denied` entries present |
| `test_main_cli.py` | CLI: parser defaults (127.0.0.1:8819), no-command returns 2, certfile/keyfile pairing enforced |
| `test_negative_control.py` | The deployment slot drill (below) + the drill-record pins |
| `test_specs.py` | Spec integrity: exact 6-fork membership, sheet schema, record fields, Moderate/L2/Certified tier fields, descriptions byte-equal to the census copies, the literal claim tables and the 34-claim histogram, verbatim evidence, classification fields pinned against `remainder/nosignal_report.json`, the classification/claims streams never mix, the SAP catalogue exclusion, the DD-CIE split artifact, absent-technology token pins, near-miss confinement (machine learning only in Elastic; endpoint management only in IBM) |
| `smoke.py` | — Live smoke driver (not a unittest): real server, org + member, provider, tenancy, environment activated, deployment activated, second same-workload activation refused 400, account + utilization, report counts. Prints `SMOKE OK`. |

## Negative control (mutation-verified)

Signature invariant: **the deployment slot rule** — within one
tenancy, at most one deployment of a given workload reference may
be active at a time, enforced by `CloudInfraStore._check_deployment_slot`
on activation (Core function 5, SI-10).

Two layers, as everywhere in this repo:

1. **In-suite mutant** (`test_negative_control.py`): a
   `CloudInfraStore` subclass whose `_check_deployment_slot` does
   nothing. The canonical test proves the real store refuses the
   second activation and changes nothing; the mutant test proves
   the mutant waves it through, and that asserting the mutant's
   outcome as the expectation raises `AssertionError` — so the
   tests test the invariant, not that code ran.
2. **Recorded file-level drill** (`mutation-run.txt`,
   `store.py.premutation`, `store.py.sha256`): the seam body in
   `src/cloudinfra/store.py` was replaced with `return None` and
   the full suite re-run. **Exactly 4 failures**, all slot-related:
   `test_slot_rule_blocks_second_active_same_workload`,
   `test_canonical_expectation_refuses_second_activation`,
   `test_end_to_end_flow` (the HTTP refusal), and the
   byte-identical pin (expected to fail while mutated). One
   further error in the drill run — `test_mutation_run_recorded`
   — is the record not existing yet while the drill runs; it
   passes once `mutation-run.txt` is written. The store was then
   restored byte-identical (SHA-256 verified against
   `tests/store.py.sha256`) and the suite re-verified at 118/118
   green.

## Smoke

`PYTHONPATH=src python3 tests/smoke.py` — real server on an
ephemeral port, real requests, prints `SMOKE OK`.
