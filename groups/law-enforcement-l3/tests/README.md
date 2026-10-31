# Law Enforcement L3-adjacent — test suite

**110 tests, all passing** (Python standard-library `unittest` only;
no third-party dependencies). Inherited from Group 34's suite
(82 tests), with the adaptations listed below plus 20 new tests for
the High-baseline uplifts (1 in `test_access.py`, 19 in
`test_l3_uplifts.py`), plus 8 remainder-addition tests in
`test_additions.py` (see the additions section at the end).

## Running

```bash
cd groups/law-enforcement-l3
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
# -> Ran 110 tests ... OK
```

(`PYTHONPATH=src` is the documented runner, as in Group 34; the
shared helpers also add `src/` to the path for standalone runs. The
JSONL audit tests write under `../scratch/`, which the suite creates
and which is gitignored.)

## Layout

| File | Tests | Covers |
| --- | --- | --- |
| `lawenf_helpers.py` | — | Canonical fixtures: store + audit + one matter (bob creates, carol member); users alice/bob/carol/**dana**/mallory; `fresh_store` / `make_store`; document content + SHA-256; query/note fixture texts |
| `test_matters.py` | 15 | Core 1: matter lifecycle, membership boundary, close/reopen, validation |
| `test_sources.py` | 8 | Core 2: source registry kinds, citation refs, lifecycle |
| `test_documents.py` | 13 | Cores 3–4: document registry key shape, review lifecycle, verify-by-content (exact bytes match, altered do not) |
| `test_searches_annotations.py` | 10 | Cores 5–6: digest-only saved searches and annotations |
| `test_citation_checks.py` | 6 | Core 7: verbatim treatment, no score field |
| `test_reports_search.py` | 7 | Core 8: counts-only reporting, metadata-only search |
| `test_service.py` | 5 | Core 9 surface: live HTTP, envelopes, `:denied` auditing, full flow, digest discipline over the wire |
| `test_access.py` | 7 | Core 10: permission matrix for admin/member/viewer **plus the [L3] auditor role (`audit_read` only)** |
| `test_audit.py` | 5 | Core 11: entry shape (now including the [L3] chain fields), JSONL persistence, store action names, failed ops record nothing |
| `test_privacy.py` | 4 | **HARD PRIVACY RULE**: pinned key sets, smuggled-field rejection (incl. fields the store signature cannot accept), digest non-searchability |
| `test_negative_control.py` | 2 | Inherited in-suite negative controls (see below) |
| `test_main_cli.py` | 1 | `python -m lawenf serve` boots, answers `/health`, serves a request |
| `test_l3_uplifts.py` | 19 | **New for Group 35**: hash chain + tamper negative control, audit query, fail-closed rollback (log and store level), auditor role over HTTP, `/audit/verify`, audit filters over HTTP, AC-7 lockout (incl. success-resets), CLI lockout flags |
| `test_additions.py` | 8 | Remainder addition (`addition:law-enforcement-l3`): spec integrity for the TRAPWIRE sheet (membership, all-zero claim tables, verbatim descriptions, census citations, near-miss and category-discipline token pins) + 2 substrate cases in the newcomer's shape (protection-network membership boundary; report record integrity + counts) |

## Adaptations from Group 34's suite

- `lawenf_helpers.py`: one additive user — `AUDITOR = dana/auditor`
  (and `USERS` gains `"dana": "auditor"`).
- `test_access.py`: +1 test pinning the auditor role to exactly
  `{"audit_read"}` (AC-5 separation of duties).
- `test_audit.py`: the entry-shape assertion now expects the eight
  keys including the [L3] chain fields `seq` / `prev_hash` / `hash`.
- `test_main_cli.py`, `test_negative_control.py`: docstring notes
  only (demo-user list; Group 35 inheritance note).
- Every other inherited file is byte-identical to Group 34's.

## Negative controls

Three, all mutation-verified:

1. **Membership guard (inherited, in-suite)** — a
   `MutantMembershipStore` whose guard always allows must be
   rejected: the real store denies the outsider on read and write,
   the mutant admits, and the control's canonical store-side
   assertions fail against the mutant.
2. **Verify-by-content (inherited, in-suite)** — a
   `MutantVerifyStore` whose verify always reports a match must be
   rejected: altered bytes must not match.
3. **Audit tamper (new, in-suite, `test_l3_uplifts.py`)** — a
   pristine log verifies `(True, None)`; mutating entry 1's actor in
   place makes `verify_chain()` return `(False, 1)`; a stripped
   `hash` field and a rewritten `prev_hash` are localized likewise;
   and editing one line of the persisted JSONL file is detected
   after reload at exactly index 1.

### External drill record (against the real source)

Performed for this group, per the merged-build contract:

- Copied `src/lawenf/store.py` aside
  (`scratch/store.py.premutation`, SHA-256
  `18070d5545505462439c5f62f76e2ce93ce428c8fb17774107f50c40bb2a6350`)
  and replaced the `_require_matter_access` guard's
  `PermissionDenied` raise with `return None`.
- Full suite against the mutant: **102 ran, 5 failures** —
  `test_negative_control` (canonical denial), `test_service`
  full-flow (outsider 403 step), `test_sources`
  outsider-cannot-list, `test_matters` outsider read denied and
  outsider scoped-write denied. The list is preserved at
  `scratch/mutation-drill-failures.txt`.
- Restored `store.py` from the copy; SHA-256 verified identical to
  the pre-mutation hash; full suite green again (**102/102 OK**).

## Honesty notes

- All counts above are from actual runs of this suite in this
  directory.
- The AC-7 lockout's **time-based expiry** is exercised by code
  construction (`_is_locked` compares against the injected clock and
  clears expired locks) and by the threshold/reset tests; no test
  sleeps for the 300-second default.
- The documented runner above (`PYTHONPATH=src`) is the supported
  invocation, as in Group 34.

## Remainder addition (unit `addition:law-enforcement-l3`)

The suite grows **102 → 110 tests** with `tests/test_additions.py`
(8 tests), pinning the remainder addition (TRAPWIRE Threat
Detection and Analysis System, `F1602057825A`) spec'd under the
group's verbatim 9-family taxonomy: sheet count / append order /
membership against `remainder.json`, the literal claim tables
(all three sheets empty — the newcomer is the group's third
zero-claim sheet, 0 raw hits across all 9 families),
descriptions equal to the cached marketplace text, both census
citations verifying verbatim and tagging nothing, the near-miss
pins ("Cross-organizational collaboration" is not the verbatim
`collaboration` phrase; "secure web access" is not "secure
access controls"; the description contains no "cloud", "search",
or "document" token), the category-discipline pins (no facial /
recognition / surveillance / camera / sensor / predict token;
"real-time" present in the fork's own words; "criminal" exactly
once, naming acts), and two substrate cases in the newcomer's
shape (a protection-network matter whose membership boundary
denies an outsider; a report record held as metadata + checksum
with verify-by-content and counts on read). See `ADDENDUM.md`.

**Drill re-run in this tree (additions).** The group's signature
membership-guard drill was re-run against the enlarged suite:
the `PermissionDenied` raise in `_require_matter_access`
(`src/lawenf/store.py`) was replaced with `return None` as a
scoped replacement (target text asserted to occur exactly once)
— **110 tests ran, exactly 6 failed**: the shipped drill's 5
(`test_negative_control` canonical denial, `test_service`
full-flow, `test_sources` outsider-cannot-list, `test_matters`
outsider read denied and outsider scoped-write denied) plus
exactly 1 from the additions module,
`test_additions.TestTrapwireSubstrate.test_protection_network_membership_boundary`.
`store.py` was restored from the pre-mutation copy in `scratch/`
(`store.py.premutation-additions`) and verified SHA-256-identical
to the shipped hash (`18070d55…`); the full suite re-ran green
after the restore. Raw failure list:
`scratch/additions_mutation_run.txt`.
