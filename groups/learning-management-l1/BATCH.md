# Final GAPS batch — Remainder Group 2, Learning Management L1

Unit: the 6 OPEN entries in GAPS.md under "Remainder Group 2 —
Learning Management L1 (2 forks, new tier group)" (idx 633–638 in
`../../gaps-batch/inventory.json`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 3
build-extension, 3 stub-engine — exactly as triaged.

All extension code is in one new module, `src/lms/extensions.py`
(`LmsExtensions`, wrapping the core `LmsStore`); every existing core
module is byte-identical to its pre-batch state (SHA-256 verified
against the pre-work baseline; `store.py` still hashes to the
shipped `8986a77e…`). Full suite: 137 tests before, **170 tests
after, OK**, including the fresh mutation-verified negative
controls recorded in `tests/README.md`.

**No entry was re-judged.** On a close reading of UNION-SPEC.md
each drafted disposition fits, with the in-substrate forms stated
in the batch brief: portal rendering = presentation data bound to
the core organization registry with the current presentation
derived at read (nothing rendered); the CE engine = renewal-cycle
records whose coverage and status derive at read from the core CE
records, credit text verbatim end to end (no credit arithmetic —
the core's boundary, kept); the certificate service = issuance and
verification-query records bound to core award records (nothing
issued, nothing verified); authoring, posting, and integrations
execute against systems outside this substrate and ship as labeled
reference records.

Two boundary calls, stated rather than silent:

- **Authoring (idx 633)** carries one built-adjacent element inside
  its reference closure: check records hold a caller-reported
  outcome verbatim with `outcome_basis: caller_reported`. Recording
  a report *about* a Section 508 check is a records act; running
  the check, or certifying conformance, is not claimed anywhere on
  the surface. This does not move the token: the environment itself
  (workspace, themes/menus tooling, plugin runtime, renderer) is
  the entry's substance and it is reference.
- **Certificate verification (idx 637)** closes *built* in the
  same form the L2 sibling's batch used for its delivery and
  form-workflow surfaces: the service surface the entry names
  (issuance + verification) exists here as records bound to the
  core award, with `issued_here: False` / `verified_here: False`
  on the records themselves. A public verification *endpoint* —
  a lookup service for third parties — would be a deployment
  surface, not a records function, and is not claimed; the
  registry-side query records are the in-substrate form.

| Entry (GAPS.md text) | Disposition | Built (module: `lms/extensions.py`) |
|---|---|---|
| Learning content authoring environment: rapid / collaborative authoring, themes & menus, plugins, 508-conformant output (CloudLCMS) | reference (stub-engine) | `create_authoring_draft` (`dft-`, optional core course/content binding with the L2 mismatch rule; `reference_stub: True`, state `recorded_reference_only`), `record_authoring_session` (`asx-`, mode `individual`/`collaborative` — CloudLCMS's own distinction), `record_authoring_check` (`ack-`, kinds `section_508`/`theme_and_menus`/`plugin_review`, outcome verbatim with `outcome_basis: caller_reported`); pinned to change no core record |
| Course posting & publication workflow (TRAIN) | reference (stub-engine) | `create_publication_record` (`pub-`, channels `community_catalog`/`organization_portal`/`external_link`; an `organization_portal` posting requires a `target_org_ref` resolving to the core organization registry; `published_here: False`, `reference_stub: True`); pinned to leave the core course record byte-identical |
| Branded portal rendering & presentation engine (TRAIN) | built | `create_portal_presentation` (`ppr-`, organization_write, bound to a core organization ref, one per organization) holding brand label / theme / menu labels as data, `revise_portal_presentation` append-only; views derive `current` from the latest revision via `_current_presentation` (never stored), `rendered_here: False` on every view; pinned to leave the core organization record untouched |
| Continuing education management engine (TRAIN) | built | `create_ce_cycle` (`crc-`, period dates validated, `required_credit_text` verbatim), `get_ce_cycle` / `list_ce_cycles` — views derive `recorded_record_count`, `covered_activity_refs`, `credit_texts` (verbatim strings only), and `status` via `_derive_ce_cycle_status` (`satisfied` when a qualifying core CE record exists in the period — undated records count as in-period facts — else `lapsed` past the period end, else `open`), never stored; learner scope mirrors the core |
| Certificate issuance & verification service (TRAIN) | built | `create_issuance_record` (`iss-`, bound to a core award, channel enum, `issued_here: False`, state `recorded`), `record_verification_query` (`vfy-`, outcome label verbatim, `verified_here: False`), `certificate_service_view` (core award + service records + counts derived at read); pinned to leave the core award record byte-identical and to respect the core's learner scope |
| System integration engines (TRAIN) | reference (stub-engine) | `create_integration_record` (`int-`, opaque `system_ref`, direction enum, `reference_stub: True`), `record_sync_report` (`syn-`, caller-reported outcome verbatim, optional non-negative integer `record_count` with bools rejected); pinned to change no core record |

Cross-cutting, per the group's doctrines: the founding **no-score
invariant binds the extension surface exactly as it binds the
core** — a recursive key scan over every extension record, view,
and derivation finds no `score` / `grade` key, pinned in
`test_gaps_batch.TestCrossCutting`; credit text is read only as
verbatim strings (the CE view test asserts no numeric value under
any credit-named key); all parties are opaque `*_ref` strings;
derived values are derived at read and never stored (portal current
presentation, CE coverage and status, certificate service counts);
RBAC reuses the core permission actions (catalog for
authoring/publication, organization for portal presentations,
continuing_ed for CE cycles, certificate for the certificate
service, workflow for integrations) with learner scope mirroring
the store; every successful mutation is recorded on the core audit
log with an `ext_`-prefixed action; denied writes consume no id
(pinned).

One build note, recorded for honesty: at this tier `catalog_write`
is admin-only in the core permission matrix (the instructor write
set excludes it), so the authoring and publication surfaces are
admin-operated here even though the L2 sibling's equivalents sit
under broader instructor writes at Moderate. That is the L1
baseline's own matrix, applied as shipped — not a narrowing
introduced by this unit.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
