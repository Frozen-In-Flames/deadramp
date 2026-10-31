# Cloud Infrastructure & Hosting L3-adjacent — tests

Stdlib `unittest` only. Every test docstring names the core
function or spec property it pins. 166 tests.

The suite is the founding L2 suite carried up whole (its module
set and cases unchanged, except where this tier's facts differ —
the spec module is this group's own, the helpers gain the
auditor, and the CLI module gains the lockout-flag class) plus
four uplift modules for the High baseline (`test_audit_chain.py`,
`test_audit_failure.py`, `test_audit_query.py`, `test_lockout.py`)
and the auditor class in `test_access_audit.py`.

## Run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 166 tests
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
| `test_access_audit.py` | Substrate carried: role ladder facts (admin 11 actions; member lacks org_write/audit_read; viewer read-only), require() validation, audit copy-on-read, JSONL persistence round-trip. **[L3]** `TestAuditorRole`: the auditor role holds `audit_read` only and can require nothing else (AC-5 technical slice) |
| `test_audit_chain.py` | **[L3] AU-9/AU-3**: chain fields (`seq`/`prev_hash`/`hash`), genesis link, hash recomputed independently as SHA-256 of canonical JSON, verify_chain localizes in-place edits / stripped hash fields / deletions / rewritten links, JSONL round-trip, edited-line detection after reload, and the `GET /audit/verify` endpoint (admin and auditor allowed; member denied; count read before its own audit entry) |
| `test_audit_failure.py` | **[L3] AU-5**: a failed JSONL append raises `AuditWriteError` and rolls back the in-memory append; the chain continues cleanly afterwards; store mutations roll back whole (records and id counters) when their audit write fails; the HTTP layer answers exactly 500 `{"error": "audit write failed"}` and the operation does not proceed |
| `test_audit_query.py` | **[L3] AU-7**: `query()` filters (actor/action/target/since/until, inclusive, conjunctive) over pinned timestamps; `GET /audit` filter parameters with a count; the auditor may query; an unfiltered `GET /audit` keeps the founding shape (no `count` key) |
| `test_lockout.py` | **[L3] AC-7**: 3 consecutive authentication failures lock the username (correct role then gets 403 with the lockout body, audited `auth:locked`); per-user isolation; unknown usernames lock too; a success resets the counter; authenticated permission 403s never count; a zero-second lock expires and clears itself |
| `test_privacy.py` | Privacy discipline: recursive field-name scan across every entity view and the report (no credential/content/identifier field), derived values absent from stored records, no store signature accepts a content/credential parameter |
| `test_service.py` | HTTP layer (carried): health, 401 on missing/mismatched auth, end-to-end flow incl. the slot refusal as 400, viewer write 403, 404, validation 400, audit endpoint admin-only with `:denied` entries present |
| `test_main_cli.py` | CLI (carried): parser defaults (127.0.0.1:8819), no-command returns 2, certfile/keyfile pairing enforced. **[L3]** lockout flag defaults (3 / 300) and parsing |
| `test_negative_control.py` | The deployment slot drill (below) + the drill-record pins for **both** drills at this tier |
| `test_specs.py` | Spec integrity: exact 6-fork membership, sheet schema, record fields, High/L3-adjacent tier fields taken from the registry records, descriptions byte-equal to the census copies, the literal claim tables and the 19-claim histogram, the two zero-claim forks pinned, verbatim evidence, classification fields pinned against `remainder/nosignal_report.json`, the classification/claims streams never mix, the duplicate-pair pins, the IT-CNP prose-assertion pin, the four families silent at this tier, absent-technology token pins, near-miss confinement and the itemized near-miss pins. **Taxonomy-verbatim proof**: the founding taxonomy ast-parsed from both extractors, the founding group's shipped tables reproduced deep-equal from its descriptions, and this group's tables recomputed from the census descriptions |
| `smoke.py` | — Live smoke driver (not a unittest): real server, org + member, provider, tenancy, environment activated, deployment activated, second same-workload activation refused 400, account + utilization, report counts. Prints `SMOKE OK`. Carried verbatim from founding |

## Negative controls (mutation-verified, two seams)

**Seam 1 — the deployment slot rule** (carried invariant, Core
function 5, SI-10): within one tenancy, at most one deployment of
a given workload reference may be active at a time, enforced by
`CloudInfraStore._check_deployment_slot` on activation.

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
   the full suite re-run. **Exactly 4 failures**, all
   slot-related: `test_slot_rule_blocks_second_active_same_workload`,
   `test_canonical_expectation_refuses_second_activation`,
   `test_end_to_end_flow` (the HTTP refusal), and the
   byte-identical pin (expected to fail while mutated). Three
   further errors in that run — `test_mutation_run_recorded` and
   the two `TestAuditDrillRecord` tests — are the drill records
   not existing yet while the drills were running; they pass once
   the records are written. The failure set is identical to the
   founding L2 drill's. The store was then restored
   byte-identical (SHA-256 verified against
   `tests/store.py.sha256`) and the suite re-verified green.

**Seam 2 — the audit hash chain** (new at this tier, AU-9):
`_entry_hash` in `src/cloudinfra/audit.py` computes each entry's
SHA-256 link to its predecessor; a stripped hash field, a deleted
entry, or a rewritten link must each fail verification, and an
edited entry must fail at its own index.

1. **In-suite discrimination** (`test_audit_chain.py`): the hash
   is recomputed independently with `hashlib` (not via the
   module's own function), and the tamper cases assert
   `verify_chain()` returns `(False, index)` — so a constant or
   self-consistent-but-wrong hash cannot pass.
2. **Recorded file-level drill** (`audit-mutation-run.txt`,
   `audit.py.premutation`, `audit.py.sha256`): `_entry_hash` was
   replaced with the constant `"0" * 64` and the full suite
   re-run. **Exactly 4 failures**: `test_hash_is_sha256_of_canonical_json`,
   `test_in_place_edit_localized`,
   `test_edited_jsonl_line_fails_verification_after_reload`, and
   the byte-identical pin (expected to fail while mutated). One
   further error — `test_audit_mutation_run_recorded` — is the
   record not existing yet while the drill runs; it passes once
   `audit-mutation-run.txt` is written. Under a constant hash the
   chain still self-links and a clean log still verifies, so the
   three discriminating failures are exactly the tests that tell
   a real hash from a constant; the structural tamper cases
   (stripped field, deletion, rewritten link) fail verification
   in both worlds and pass under the mutant too. The file was
   then restored byte-identical (SHA-256 verified against
   `tests/audit.py.sha256`) and the suite re-verified at 166/166
   green.

## Smoke

`PYTHONPATH=src python3 tests/smoke.py` — real server on an
ephemeral port, real requests, prints `SMOKE OK`.
