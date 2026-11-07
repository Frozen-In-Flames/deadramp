# Tests — CRM untiered set build

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to.

## Run

```bash
cd groups/crm-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 104 tests
```

Status at delivery: **104 tests, OK** against the implementation
in `../src/`. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Provenance

The founding CRM L2 group's 96-test suite is carried whole with
the code (all 14 test modules byte-identical to
`../../crm-l2/tests/`), with **one labeling fix** in
`crm_helpers.py`: its docstring now names this untiered set as
the carrier of Group 25's suite instead of naming the L2 build.
No test logic was changed. Added here: `test_specs.py` (8 tests)
pinning this set's spec sheet. 96 + 8 = **104 tests**.

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/operator/viewer (14 actions), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_registry.py` | Account & contact registry — `acct-`/`ct-` creation shape/provenance/defaults, opaque reference required + unique (duplicates rejected), unknown account → `NotFoundError`, list filter by account, copies-are-copies, viewer write denied, failed ops consume no ids |
| `test_privacy.py` | Privacy discipline — no entity shape (account/contact/case/interaction/guide/finding/module) carries a name/email/phone/ssn/dob/address/salary/score field; finding detail stored verbatim; the report contains no score/average aggregate |
| `test_cases.py` | Cases — creation/validation (types, priorities, due_at parsing, referenced ids, contact↔account consistency), assignment, full lifecycle + reopen + cancel paths, invalid transitions, breach derivation (overdue open/in_progress breached; future/no/exact due not breached; terminal statuses never breached; `now` as string/datetime/None; derived-not-stored), list filters, no-id-on-failure |
| `test_interactions.py` | Interactions — `int-` recording, all channels/directions, validation + linked-id checks + contact↔account consistency, immutability (no update/delete API on the store; returned records are copies), case/account filters |
| `test_guides.py` | Guides — `guide-` creation at version 1 with versions list, all kinds, validation (title/target/steps/enabled), versioned updates carrying unchanged fields forward, copies-are-copies (deep), viewer write denied |
| `test_findings.py` | Findings — `find-` creation with verbatim detail, severities, lifecycle open→acknowledged→addressed + dismiss paths, invalid transitions, status/account filters |
| `test_modules.py` | Modules — `mod-` creation at version 1 with versions list, validation, **admin-only write (operator and viewer denied)**, versioned updates, viewer read allowed |
| `test_reports_search.py` | Reports + search — report shape/counts (cases by status/type/account incl. `unassigned`, breached at `now`; interactions by channel/outcome incl. `none`; guides by kind/enabled; findings by severity/status; module totals), now-dependence of breach counts, empty store; search shape `{accounts, contacts, cases, interactions, findings, guides}`, label+reference / subject / summary / title matching, literal-not-regex, empty query → `ValidationError`, search audited |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording every contract mutation action name, failed ops record nothing |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer write + config_write for operator (denied attempts audited with `:denied`), full flow (account → contact → case → assign/transition → interaction → guide create/PATCH → finding → module → report/search), `audit_read` admin-only, 400/404 envelopes, `?now=` derivation on case/report endpoints |
| `test_main_cli.py` | `python -m crm serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `test_specs.py` | **This set's spec pins** — exactly 1 sheet; fork_id set == remainder.json unit `untiered:Customer Relations Management (CRM)`; tier discipline (`cmmc_tier` null, impact `"Unknown"`); every claim's evidence a verbatim substring of the description; the description byte-equal to the raw cache's `service_desc`; `deadramp_category` `"CRM"`; literal totals (exactly 2 claims, families exactly {`account_contact_registry`, `ai_scoring`}, zero-claim set empty); catalogue discipline (the record's `certified_services` asserts "Sales pipeline" yet `opportunity_pipeline` is not claimed) |
| `test_gaps_batch.py` | Final GAPS batch extensions — per-entry surface pins for the 4 batch entries (proposal-generation request/report/evaluation records, forecast request/report/figure records + counts-only summary, document template/request/report records, connector definitions/syncs/catalog), audit + rollback + reference-label + tier-null/no-score recursive-scan invariants, and the batch's fresh negative control (below) |
| `crm_helpers.py` | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a CrmStore + AuditLog + an account + a contact under it |

## Negative control

`test_negative_control.py` implements the contract's required
mutant: a `CrmStore` subclass (`MutantCrmStore`) overriding the
derivation point — `_is_breached` always returns `False`. The
traced claim, named in the module's docstrings, is that **breach
derivation happens at read time**: an overdue open case must read
`breached=True` (and a report at that `now` must count it
breached). The test asserts three things: the canonical
expectation (derived value from the real implementation, including
the report count), that the mutant would NOT produce that
expectation (it reads not-breached, and its report counts zero
breached), and — via a literal `assertRaises(AssertionError)` —
that treating the mutant's outcome as the expected outcome fails.

## Mutation verification

VERIFIED by the builder (2026-10-31), live drill performed on the
real implementation in THIS tree (not just the subclass mutant) —
the founding group's recorded signature drill, re-run here. The
body of `CrmStore._is_breached` (`src/crm/store.py`) — the single
derivation point for case SLA breach — was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`, so an overdue open case never read
breached. The full suite was run: **104 tests ran, 7 failed** —
the founding drill's identical failure set, and no spec test
tripped:

- `test_cases.TestBreachDerivation.test_in_progress_past_due_breached`
- `test_cases.TestBreachDerivation.test_now_forms`
- `test_cases.TestBreachDerivation.test_overdue_open_case_breached`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_case_breached_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_breach_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestService.test_full_flow`

(Full output in `scratch/drill_failures.txt`.) `store.py` was
then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`16bcc12fa6b55dec54bf76f150b1619834400ba93ee4687df5dffe2990fe2f1a`,
recorded in `scratch/store.py.sha256` and verified identical
after restore — the same hash as the founding group's shipped
`store.py`, as the byte-identity accounting requires) and the
suite re-run: **104 tests, OK**. The suite catches this defect
class; the negative control is not decorative.

## Final GAPS batch additions (2026-11-07)

The batch unit for this set (see `../BATCH.md`) added
`tests/test_gaps_batch.py` (29 tests): **133 tests, OK** in total.
All 7 pre-existing core modules are byte-identical to their
pre-batch state (SHA-256 verified; `store.py` still `16bcc12f…`).
The one new module is `src/crm/extensions.py` (SHA-256
`0c9fa7b5…`).

### Batch negative control (fresh, for the new code)

`test_gaps_batch.TestNegativeControlConnectorRollup` implements
the batch's mutant: a `CrmExtensions` subclass
(`MutantCrmExtensions`) overriding the derivation point —
`CrmExtensions._sync_rollup` returns `{}`. The traced claim is
that **the connector catalog's per-connector rollup is derived
at read from the recorded sync receipts** — receipt counts, sums
of the connectors' own reported record counts, and receipt
counts by direction. The test asserts the canonical expectation
(ext-crm: 3 syncs, reported total 9, `{inbound: 2, outbound: 1}`;
ext-erp: 1 sync, reported total 7, `{inbound: 1}`), that the
mutant does NOT produce it (it reports no connectors at all),
and — via a literal `assertRaises(AssertionError)` — that
treating the mutant's outcome as the expected outcome fails.

### Batch mutation verification

VERIFIED by the builder (2026-11-07), live drill performed on
the real extension module in THIS tree. The total-accumulation
line of `CrmExtensions._sync_rollup` (`src/crm/extensions.py`) —
the single derivation point for the catalog's per-connector
reported totals — was patched from
`entry["records_reported_total"] += sync["records_reported"]`
to `entry["records_reported_total"] += 0` (the line occurs
exactly once), so receipts register but their reported counts
never accumulate. The full suite was run: **133 tests ran,
exactly 2 failed** —

- `test_gaps_batch.TestConnectorEngines.test_catalog_rollup_is_derived`
- `test_gaps_batch.TestNegativeControlConnectorRollup.test_canonical_rollup_but_mutant_does_not`

`extensions.py` was then restored from a pre-mutation copy
(`scratch/extensions.py.premutation_gaps`; SHA-256
`0c9fa7b54c58b43032acc98926e8d21cc38e8a6ba2020c2f4e23d437b4a58490`,
recorded in `scratch/extensions.py.sha256_gaps` and verified
identical after restore) and the suite re-run: **133 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.
