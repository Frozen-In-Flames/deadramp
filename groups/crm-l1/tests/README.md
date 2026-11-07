# Tests — CRM L1 singleton build

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to. The suite is Group
25's (CRM L2), reused: 13 of 15 test files are byte-identical to
Group 25's, and the 2 differing files differ in documentation
wording only (see `../scratch/reuse-note.md`). No test logic
changed. What the suite verifies does not change with the tier —
the carried substrate's behavior is identical; what changes at L1
is the baseline the behavior is claimed against (UNION-SPEC.md),
not the code. One new file (`test_singleton_spec.py`) pins this
singleton's spec sheet and runs two substrate cases in the fork's
shape.

## Run

```bash
cd groups/crm-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 108 tests
```

Status at delivery: **108 tests, OK** against the implementation
in `../src/`. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_singleton_spec.py` | **This singleton** — spec integrity: single sheet == census unit membership, taxonomy verbatim across tiers (ast-parsed from both sibling extractors), the literal claim table (`ai_scoring` only, pinned evidence), the 17-family zero-claim set, tier fields (LI-SaaS recorded as-is), description == cached source verbatim, census citation verifies and tags nothing, no-exclusion accounting, near-miss pins; plus 2 substrate cases in the fork's shape (channel interaction records over the registry; a verbatim finding under the recursive no-score scan) |
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

At this tier the derivation stands as a design property of the
carried substrate (this singleton's fork claims no case function),
traced to CM-6 / AU-2 at the Low baseline in UNION-SPEC.md rather
than to a sibling's evidenced claim — the re-anchoring is recorded
in the module's docstring, one of the two documentation-only
differences from Group 25's suite.

## Mutation verification

VERIFIED by the builder (2026-10-31), live drill performed on the
real implementation in THIS tree (not just the subclass mutant).
The body of `CrmStore._is_breached` (`src/crm/store.py`) — the
single derivation point for case SLA breach — was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`, so an overdue open case never read
breached. The full suite was run: **108 tests ran, 7 failed** —

- `test_cases.TestBreachDerivation.test_in_progress_past_due_breached`
- `test_cases.TestBreachDerivation.test_now_forms`
- `test_cases.TestBreachDerivation.test_overdue_open_case_breached`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_case_breached_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_breach_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestService.test_full_flow`

— the same 7 failures as Group 25's drill, and none from
`test_singleton_spec.py` (its substrate cases deliberately do not
touch the derivation). Raw list in `../scratch/drill_failures.txt`.

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`16bcc12fa6b55dec54bf76f150b1619834400ba93ee4687df5dffe2990fe2f1a`,
recorded in `scratch/store.py.sha256` and verified identical after
restore — and identical to Group 25's shipped `store.py`) and the
suite re-run: **108 tests, OK**. The suite catches this defect
class; the negative control is not decorative.

## Final GAPS batch tests (appended at the batch build)

| Module | What it pins |
|---|---|
| `test_gaps_batch.py` | The 8 open entries of this singleton's GAPS.md section (idx 683–690), closed in `../BATCH.md`: the CXM platform records surface (channel-surface definitions pinned to an exact key set; the experience overview derived at read as deterministic counts), the social publishing / listening / advertising / orchestration / marketing / AI reference surfaces (every record `reference_stub: True`, outcome receipts `reference_transport: True` where the L2 forms carry it, definitions held as data and pinned to execute nothing and change no core record), care engagement depth in the L2 casework form (desktop compositions over existing records, topic enable/disable, chat sessions as labeled reference records bound to core cases), the privacy rule by signature (a content argument to the publishing surface and a result argument to the AI surface raise `TypeError`), score-shaped labels refused at the boundary, a recursive no-score-key scan over every stored extension record and derived view, RBAC denials audited as `ext_*:denied`, and failed-audit-write rollback (insertion and id roll back). 36 tests; suite total after the batch: **144 tests, OK** (108 before). |

### The channel-count seam drill (fresh negative control, batch)

The claim under test: **the experience overview's by-channel
distribution is derived at read from the recorded core
interaction records, counted by their recorded channel** — the
CXM entry's only derivation, computed at read through the seam
`CrmExtensions._channel_counts`.
`TestNegativeControlChannelCounts` pins the canonical case
(interactions on chat / email / chat read back as
`{"chat": 2, "email": 1}`) and asserts (1) the real
implementation's outcome, (2) a mutant subclass overriding the
seam to count nothing would NOT produce it, and (3) treating
the mutant's outcome as the expected outcome raises
`AssertionError`.

File-level verification (performed at build time, raw output in
`../scratch/gaps_batch_mutation_run.txt`): the shipped
`src/crm/extensions.py` (pre-mutation SHA-256
`5f0d34691529a1fbcd7bdcd0fa1979a6b910619f47b6d3a39691c29493614c77`,
backup in `../scratch/extensions.py.premutation`) was mutated at
the seam's counting line (`counts[channel] = counts.get(channel,
0) + 1` → `counts[channel] = counts.get(channel, 0)`, exact
full-line match, one occurrence) and the full suite run: **144
ran, exactly 2 failures** —

- `test_gaps_batch.TestCxmPlatformRecords.test_overview_is_derived_counts_only`
- `test_gaps_batch.TestNegativeControlChannelCounts.test_canonical_counts_but_mutant_does_not`

— both in the batch's own new tests and both
derivation-dependent; no core or founding test failed. The file
was then restored from the pre-mutation copy, its SHA-256
verified identical, and the suite re-run green: **144 tests,
OK**.
