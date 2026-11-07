# Tests — Law Enforcement untiered set (Untiered Set 17)

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to. The core suite is the founding
group's (Law Enforcement L2) suite carried with the code — the
founding L2 group has no additions module, so the carry is the full
founding suite — plus `test_specs.py`, new for this untiered set.
The one carried-file edit is a labeling fix in `lawenf_helpers.py`
(its docstring names this untiered set instead of L2); no test logic
was changed.

## Run

```bash
cd groups/law-enforcement-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 91 tests
```

Status at delivery: **91 tests, OK** against the implementation in
`../src/` (82 carried founding core tests + 9 new spec tests). (Run
exactly as above: helpers are imported as a top-level module from
the tests directory and `tests/__init__.py` is empty by design, so
package-mode discovery with `-t .` is not the supported entry point
for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/member/viewer over the 9 contract actions, `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, copies-are-copies, JSONL persistence + reload (in group `scratch/`), the store recording every contract mutation action name, failed ops recording nothing |
| `test_matters.py` | Matter registry — creation shape pinned, duplicate/empty ref rejected (no id consumed), viewer cannot create; the membership boundary (outsider read/write denied, outsider lists empty, admin bypass, unknown matter 404-class); add-member rule (creator or admin only, duplicates rejected); close/reopen guards and closed-matter write rejection |
| `test_sources.py` | Source registry — shape pinned, all six kinds accepted, unknown kind rejected (no id consumed), per-matter ref uniqueness, cross-matter get is NotFound, kind filter, outsider denied |
| `test_documents.py` | Document registry — shape pinned, checksum must be 64 lowercase hex, size must be a non-negative int (bool/float rejected), duplicate ref rejected; review lifecycle `registered → in_review → reviewed` with skip/terminal transitions rejected; verify-by-content: exact bytes match, str is UTF-8-encoded, tampered bytes do not match, verify is non-mutating |
| `test_searches_annotations.py` | Saved searches & annotations — digest-only shapes (no `query`/`note` keys exist), store signatures contain no text parameter, digest/count validation, duplicate refs rejected, all three annotation target kinds, unknown kind / missing target / cross-matter target rejected, target filter |
| `test_citation_checks.py` | Citation checks — shape pinned, treatment stored **verbatim** (casing/punctuation preserved), no score/status/valid field exists, empty treatment rejected, source link must exist in the matter, repeat checks allowed |
| `test_reports_search.py` | Reporting & registry search — counts by kind/status, treatment counts keyed verbatim (`followed` ≠ `Followed`), empty-matter report; literal (non-regex) search over refs/kinds/treatments, **digests are not searchable**, outsider sees nothing, empty query rejected |
| `test_privacy.py` | The hard privacy rule — every entity's exact key set pinned; no field named for a person, subject, or content; smuggled fields (`subject_name`, `content`, `query_text`, `note_text`) rejected by the store signatures themselves; returned records are copies |
| `test_service.py` | REST API — live HTTP server: health without auth, 401 unknown user / role mismatch, 404 envelope, viewer write → 403 audited `matter_write:denied`; full flow (matter → member → source → document → review lifecycle → verify match/mismatch/bad-base64 → saved search with `query_text` hashed by the service and never stored → annotation digest → citation check verbatim → report → audit admin-only → registry search scoped by membership → closed matter rejects writes with 400) |
| `test_main_cli.py` | `python -m lawenf serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative controls (below) |
| `test_specs.py` | **New for this set** — spec integrity for the 2 untiered forks: sheet count exactly 2; fork_id set == the fork_ids set of remainder.json unit `untiered:Law Enforcement`; tier discipline (every sheet's `cmmc_tier` is None and `fedramp_impact_level` is `"Unknown"`); claim evidence verbatim (vacuous at 0 claims, standing so no claim can drift in unverified); every sheet's `deadramp_category` is `"Law Enforcement"`; literal claim totals pinned (exactly 0 claims; the zero-claim set is exactly {FR2628943632, FR2631258113}); **category-discipline tokens** (`facial`, `predictive`, `surveillance`, `camera`, `sensor`, and the phrase `real-time intelligence`) occur 0 times in each description; descriptions exact against `remainder/uncovered.json`; census citations verify verbatim (2/2) and serve as no claim's evidence |
| `lawenf_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `USERS` registry, canonical digests, `fresh_store()`, and `make_store()` building a LawEnfStore + AuditLog + one matter (MEMBER's, VIEWER added as a member). Docstring relabeled for this set; code unchanged |

## Negative controls

`test_negative_control.py` implements the contract's two required
mutants as store subclasses (carried from the founding group):

1. **Membership-guard mutant** (`MutantMembershipStore`):
   `_require_matter_access` performs no check, so any authenticated
   actor can read any matter. The canonical test asserts the real
   store denies the outsider (`PermissionDenied`, empty lists, empty
   search), that the mutant waves the read through, and that treating
   the mutant's outcome as the expectation raises `AssertionError`.
2. **Verify mutant** (`MutantVerifyStore`): `verify_document` reports
   `matches: True` for any content. The canonical test asserts the
   real store reports altered bytes as `matches: False`, that the
   mutant waves the tampering through, and that treating the mutant's
   outcome as the expectation raises `AssertionError`.

### Mutation verification (the drill, performed on this tree)

The founding group's signature drill was re-run in this tree:
`LawEnfStore._require_matter_access` in `src/lawenf/store.py` was
patched to a no-op (`return`), and the suite was run:

```
Ran 91 tests — FAILED (failures=5)
  test_matters.TestMembershipBoundary.test_outsider_read_denied
  test_matters.TestMembershipBoundary.test_outsider_scoped_write_denied
  test_sources.TestSources.test_outsider_cannot_list
  test_negative_control.TestMembershipGuardNegativeControl
      .test_canonical_denial_and_mutant_rejection
  test_service.TestFullFlow.test_flow
```

Exactly 5 failures — the founding drill's identical failure set (the
founding run was over its 82-test suite; the 9 new spec tests do not
touch the store and none failed). No spec test failed. `store.py` was
then restored from `scratch/store.py.premutation` and verified
**SHA-256-identical** (`13c8649dd24ee8372b6aa699cd47d9d5071eecdeb08bc31e204f0528ae4d3366`,
recorded in `scratch/store.py.sha256` — the founding shipped hash);
the suite is green again (91, OK). Raw drill output:
`scratch/mutation-run.txt`.

## Final GAPS batch tests (appended at the batch build)

| Module | What it pins |
|---|---|
| `test_gaps_batch.py` | The open functions of this set's gap list closed in records form (operations & plans, coordination messages & receipts, location reports, after-action reports, chain references & reported links, leads & reported links, investigation requests & opaque results) plus the operational risk-assessment reference records: every record's exact key set and boundary labels, ref-uniqueness and no-id-on-failure, cross-matter isolation, derived-never-stored counts and degrees, the privacy rule by signature (smuggled content / body-text / query-text / note-text / person / identifier / address / coordinate kwargs raise `TypeError`), digest fields accepting only 64-hex digests, the tier-null recursive scan (no tier/baseline/equivalence key, no score/rating/grade key, no person/content key, no float, no numeric list on any extension record or view), reference-stub and reference-transport labels, the RBAC mapping onto the core action set, the membership boundary, the closed-matter rule, and `ext_*` / `ext_*:denied` audit discipline. The workspace multi-tenancy entry has NO code here: it is closed in writing under `PLATFORM-LAYER.md` decision 6 (see `../BATCH.md`). |

### The chain-degree seam drill (fresh negative control, batch)

The claim under test: **a chain reference's in-degree counts the
recorded links whose target it is, and its out-degree counts the
recorded links whose source it is** -- the
blockchain-intelligence entry's only derivation, computed at
read over the link records through the seam
`LawEnfExtensions._chain_degree`.
`TestChainDegreeNegativeControl` pins the canonical case (links
A->B, A->C, B->C: A reads in 0 / out 2, C reads in 2 / out 0, an
isolated reference reads 0/0) and, for each asymmetric case,
asserts (1) the real implementation's outcome, (2) a mutant
subclass overriding the seam to swap in/out would NOT produce
it, and (3) treating the mutant's outcome as the expected
outcome raises `AssertionError`.

File-level verification (performed at build time, raw output in
`scratch/gaps_batch_mutation_run.txt`): the shipped
`src/lawenf/extensions.py` (pre-mutation SHA-256
`f7413f5a52d562942ceed22e629308a663909bfe5a9ea23ba4b1f23d04041451`,
backup in `scratch/extensions.py.premutation`) was mutated at
the seam's return line (`return in_degree, out_degree` ->
`return out_degree, in_degree`, exact full-line match, one
occurrence) and the full suite run: **exactly 3 failures** out
of 133 (the two asymmetric canonical cases in
`TestChainDegreeNegativeControl` and the degrees test in
`TestChainReferencesAndLinks`; the symmetric isolated-reference
case passes under either orientation, as expected). The file
was then restored from the pre-mutation copy, its SHA-256
verified identical, and the suite re-run green. Run count after
the batch: **133 tests, OK** (91 before: 82 carried founding
core tests + 9 spec tests; 42 added by the batch module).
