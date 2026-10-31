# Cloud Infrastructure & Hosting, untiered set — tests

Stdlib `unittest` only. Every test docstring names the core
function or spec property it pins. 119 tests.

## Run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 119 tests
PYTHONPATH=src python3 tests/smoke.py                       # live smoke
```

## Provenance

The core suite is the founding group's 118-test suite carried
with the code (the founding `test_specs.py` and
`test_negative_control.py` were replaced with this set's own,
below; every other module is byte-identical to the founding
group's). The carried modules pin the founding contract
unchanged — at tier null the substrate they exercise is
baseline-neutral, claimed against no baseline.

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
| `test_negative_control.py` | The deployment slot drill (below) + the drill-record pins — this set's own module: the drill was re-run in this tree |
| `test_specs.py` | Spec integrity for this set: exact 1-fork membership (incl. census `no-signal-set` membership, the `no_signal` flag, and empty census citations), sheet schema, record fields, tier-null discipline (impact "Unknown", cmmc_tier null, on the sheet and in the registry), description byte-equal to the census copy and to the raw cache, the literal 4-claim table, verbatim evidence, classification fields pinned against `remainder/nosignal_report.json`, the classification/claims streams never mix, the **taxonomy-verbatim reproduction proof** (AST-parsed founding taxonomy re-applied to the founding six descriptions, deep-equal vs git HEAD, 34 claims), the extractor reproducing this sheet, the catalogue exclusion removing nothing (both-ways equality), absent-token pins, the `security_services` case-artifact pin, the `hosting_platform` named-absence pin, and the documented-control tracing sentences present verbatim |
| `smoke.py` | — Live smoke driver (not a unittest): real server, org + member, provider, tenancy, environment activated, deployment activated, second same-workload activation refused 400, account + utilization, report counts. Prints `SMOKE OK`. |

## Negative control (mutation-verified)

Signature invariant: **the deployment slot rule** — within one
tenancy, at most one deployment of a given workload reference may
be active at a time, enforced by `CloudInfraStore._check_deployment_slot`
on activation (Core function 5, SI-10). This is the founding
group's signature drill, **re-run in this tree** against the
carried substrate, as the untiered method requires.

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
   the full suite re-run in this tree. **Exactly 4 failures**, all
   slot-related — the founding drill's identical set:
   `test_slot_rule_blocks_second_active_same_workload`,
   `test_canonical_expectation_refuses_second_activation`,
   `test_end_to_end_flow` (the HTTP refusal), and the
   byte-identical pin (expected to fail while mutated). One
   further error in the drill run — `test_mutation_run_recorded`
   — is the record not existing yet while the drill runs; it
   passes once `mutation-run.txt` is written. The store was then
   restored byte-identical (SHA-256 verified against
   `tests/store.py.sha256`:
   `95d39967282ea5d215687e7f96244d364c7114378d46fe84c5e19c82cad9c405`,
   also the founding group's shipped store.py) and the suite
   re-verified at 119/119 green.

## Smoke

`PYTHONPATH=src python3 tests/smoke.py` — real server on an
ephemeral port, real requests, prints `SMOKE OK`.
