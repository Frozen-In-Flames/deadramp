# Build artifacts & provenance — Cloud Infrastructure & Hosting L3-adjacent

How `specs/specs.json` was produced, and the artifacts recorded
along the way. Extractor: `scratch/extract.py` (scratch is
gitignored; the shipped spec is `specs/specs.json`). The core was
produced by copying the founding group's shipped package
(`groups/cloud-infrastructure-hosting-l2/src/cloudinfra/` at
commit 7875481) and applying the High uplifts module by module;
the test suite was likewise carried from the founding suite and
extended, not rewritten.

## Sources joined

- `raw/data_dump.json` — the GSA FedRAMP Marketplace dataset cache
  (produced by the General Services Administration, last change
  2026-10-22). Product records joined by FedRAMP ID; the cached
  `service_desc` is the claim-evidence source.
- `remainder/uncovered.json` — the remainder census's description
  copies. The extractor asserts each sheet's description is
  byte-equal to the census copy **and** the cache's `service_desc`
  (all six pass).
- `forks.json` — the Phase 1 registry: vendor, product, service
  model, impact level, status, CMMC tier, source URL. The
  extractor asserts High / L3-adjacent for all six.
- `remainder/nosignal_report.json` — the no-signal research pass:
  classification sentence + source URL per fork. The extractor
  asserts each row is `resolved`, proposes Cloud Infrastructure &
  Hosting, and flags `is_new_category` true.

## Assertions that ran at extraction

- **Taxonomy-verbatim proof, before any new fork was tagged:**
  the founding taxonomy (ast-parsed from the founding extractor,
  never executed) re-applied to the founding group's six cached
  descriptions reproduces its shipped claim tables exactly
  (deep-equal vs git HEAD; 6 sheets, 34 claims). The extractor
  asserts this on every run, and `tests/test_specs.py` pins it
  independently.
- `certified_services` is empty for all six raw records
  (asserted; the field is never matched in any case).
- Every claim's evidence is a verbatim substring of the fork's
  cached description (asserted per claim).
- `business_categories` is empty in all six raw records — the
  census's "Uncategorized (none in source)" state, carried onto
  the sheets as `business_categories_in_source: []`.
- No catalogue exclusion applies to this set (the founding
  catalogue forks are the SAP NS2 pair, not members here); the
  extractor asserts no member is a catalogue fork, so the raw
  pass is the final pass.
- Re-running the extractor reproduces `specs/specs.json`
  byte-identically (verified after the build).

## Core provenance

The founding package was copied at its shipped state and then
uplifted. Final SHA-256 accounting against the founding modules:
**0 of 7 byte-identical** — `audit.py` (hash chain, fail-closed
record, query), `store.py` (`_fail_closed` snapshot wrapper on
all 20 mutating methods), `service.py` (AC-7 lockout,
`/audit/verify`, `/audit` query parameters, fail-closed 500,
`dana`), `access.py` (`auditor` role), `errors.py`
(`AuditWriteError`), `__main__.py` (`dana`, lockout flags),
`__init__.py` (tier docstring, export). The uplift mechanics are
the proven set of the sibling High groups (`groups/analytics-l3`,
carried through `groups/development-tools-l3` and
`groups/storage-l3`), applied to this package — our own
Apache-2.0 code throughout.

Two recorded mutation drills were run in this tree and restored
byte-identical (SHA-256 verified): the deployment slot drill
(`tests/mutation-run.txt`, `tests/store.py.premutation`,
`tests/store.py.sha256`) and the audit hash drill
(`tests/audit-mutation-run.txt`, `tests/audit.py.premutation`,
`tests/audit.py.sha256`). Each failed exactly 4 tests under
mutation, with the failure sets itemized in the records and in
`tests/README.md`.

## Recorded artifacts

- **Duplicate pair, identical text (Platform Services).**
  F1208031461A's cached description is byte-identical to its
  Moderate sibling F1208031461's; the claim tables therefore
  match exactly, and the sheets differ only where the records
  differ (tier, status, deployment model is the same "Public
  Cloud"). Verified mechanically during the build and pinned by
  test.
- **Duplicate pair, divergent text (Treasury Cloud).**
  FR1801046750's description is *not* its Moderate sibling's: a
  wider service list that nonetheless claims less (10 vs 12),
  because "multitenant" is unhyphenated in the High record and
  the High record names no CDN. Recorded, not harmonized.
- **Zero-claim flagship forks.** IBM Cloud for Government and
  Oracle OCI-Gov claim zero under the founding taxonomy. Their
  descriptions were checked sentence by sentence during the
  build; the near-miss sentences are itemized in `UNION-SPEC.md`
  and pinned by test (`test_near_misses_recorded_not_repaired`).
- **Legacy classification source (SmartCloud).** The research
  pass found no current IBM product page for SmartCloud for
  Government; its classification sentence is from an IBM-hosted
  GSA IT Schedule document (Chapter 9, revised January 25, 2017)
  on ibm.com. Recorded at that weight on the sheet and in
  `UNION-SPEC.md`.
- **Dated classification source (IBM Cloud for Government).**
  Its evidence sentence is from IBM's own Service Description
  updated December 12, 2018; the current government page was also
  checked by the research pass. Recorded at that weight.
