# Final GAPS batch — Remainder Addition — Analytics L2 (+1 fork)

This note records the second GAPS-batch unit in this group
directory: the closure of the 4 open entries of the GAPS.md
section "Remainder Addition — Analytics L2 (+1 fork)" — the gap
entries `ADDENDUM.md` §5 registered when the remainder fork
NetComm / Beacon joined the founding union, all fork excess from
its own service catalogue. The first batch unit's note is
`BATCH.md` (the 14 Extended families of the founding section);
this unit covers idx 652–655 in `../../gaps-batch/inventory.json`.

**One re-judgment.** idx 653, Digital signature engine, was
drafted `build-extension` and closes **reference**, under
`DECISION.md` qualification 1; grounds in its row below and the
parent applies the `reference` token override at close. The other
three entries close with their drafted tokens (652 built,
654 reference as drafted, 655 built).

## What was built

One new module, `src/analytics/extensions_addition.py`, adding a
second wrapper class `AnalyticsExtensionsAddition` over the core
`DatasetStore`, following the first unit's conventions exactly:
core state read only through the core store's public API, no
operation writes core state, RBAC through `analytics.access`
before any state change or id allocation, denied attempts audited
on the core audit log under this unit's own `exta_` action prefix
(distinct from the first unit's `ext_`), validation before id
allocation so rejected input consumes no id. Every existing
module — the 10 core modules and the first unit's
`extensions.py` — is byte-identical (SHA-256 verified).
Full suite: 176 tests before, **196 tests after, OK** (20 new in
`tests/test_gaps_batch_addition.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Per the group's doctrines: derived values (run rollups, reported
totals) are computed at read and never stored — stored records
carry no derived key, pinned by test; totals over reported counts
are sums of *reported* values and are named as such; nothing is
computed over external data (the surface holds no dataset
reference at all — the catalogue tools, documents, workflows, and
clients are all external to the substrate and are named by opaque
ref or digest only); no computed score exists anywhere on the new
surface, pinned by a recursive key scan.

## Per-entry dispositions

| Entry (GAPS.md text) | Drafted | Closed | Built (module: `analytics/extensions_addition.py`) |
|---|---|---|---|
| Automated back-office service tools (HR, finance & property management) | build-extension | **built** | Service-tool registry: registration records naming each catalogue tool as data (`bto-`, domain from the fixed vocabulary `hr` / `finance` / `property_management`) plus automation run records recorded as reported (`btr-`, outcome verbatim from a fixed vocabulary, item counts verbatim as reported, `reported: True`, `executed_here: False` throughout). `service_tool_view` derives run count, runs-by-outcome, and the reported-items total at read. The form is this group's own scheduling shape (definitions + reported receipts, first unit `BATCH.md`) transposed to the catalogue: the registry genuinely records the tools and their reported runs; the automation itself executes on the back-office systems and is never claimed here. |
| Digital signature engine | build-extension | **reference (RE-JUDGED)** | Labeled reference implementation: signature request records (`sgq-`, document named by opaque `document_ref` plus optional SHA-256 digest validated as a digest, signer by opaque `signer_ref`; `reference_stub: True`, `signed_here: False`, `cryptography_performed_here: False`) and signature event records (`sge-`, status verbatim from a fixed vocabulary, `signed_here: False`); `signature_view` derives the event rollup at read. There is deliberately no sign or verify method on the surface (pinned by test). |
| E-workflow tooling (explicitly distinguished from the group's Extended scheduling & workflow automation family) | stub-engine | **reference** (as drafted) | Labeled reference implementation: workflow definition records (`wfr-`, ordered `{step, action}` records held as data, `reference_stub: True`, `executed_here: False`) plus run records recorded as reported (`wfx-`, outcome verbatim, `executed_here: False`); `workflow_view` derives the run rollup at read. The distinction the entry's own text draws is honored in the disposition: the Extended scheduling family targets this build's own analytics artifacts (saved views, transforms, exports) and shipped built as definitions + receipts; e-workflow tooling orchestrates business processes on the back-office systems, so its definitions and runs are labeled reference, and a test pins that defining a workflow and recording a run creates no core dataset and touches no core row. |
| Mobile client capabilities | build-extension | **built** | Client registry: registration records (`mbc-`, opaque `client_ref` unique per registry, platform label from the fixed vocabulary `ios` / `android` / `mobile_web`, `client_software_here: False` on the record's face), capability declaration records (`mbp-`, capability from a fixed vocabulary over what a client surfaces of the core; duplicate declarations rejected), and usage records recorded as reported (`mbu-`, counts verbatim, `measured_here: False`). `mobile_client_view` derives declaration counts and the reported-usage total at read. The build ships no client software and holds no build-side session (PLATFORM-LAYER.md decision 5), so there is no session record on the surface; capabilities are declarations as data and usage arrives as reported records only. |

## Re-judgment grounds (idx 653, Digital signature engine)

Drafted `build-extension`; closes `reference`:

1. **Signing is a cryptographic operation.** A digital signature
   engine's substance is producing cryptographic signatures.
   PLATFORM-LAYER.md decisions 2–3 bound every build in this repo:
   no build claims FIPS-validated cryptography, and builds perform
   no cryptography of their own except where a group's spec
   explicitly implements a mechanism. This group's spec implements
   none for signatures (its audit is a plain append-only log). A
   signature value computed here from the standard library would
   present as the fork's engine while being neither the fork's
   cryptography nor a validated module — a fake engine.
2. **The substrate holds nothing to sign.** This build's records
   are analytics records about datasets; a document to be signed
   is external, named here by opaque ref and digest only — the
   same content-never-held bound that sent the learned engines to
   reference in sibling units.
3. The honest remainder is the batch's established reference
   form — request records plus reported outcome records, labeled
   `reference_stub: True`, with the absent capability stated on
   the records' face (`signed_here: False`,
   `cryptography_performed_here: False`) and no sign/verify
   surface existing at all.

## Fresh negative control

The reported-usage total seam
(`AnalyticsExtensionsAddition._derive_reported_usage_total`): the
canonical expectation is that usage reports of 4 and 3 recorded
for one mobile client derive a `reported_usage_total` of 7 — the
total is the SUM of the recorded reports. The test module states
the expectation once, asserts the real implementation meets it,
and asserts a first-count-echo subclass mutant (the seam returns
the first report's count instead of summing) is rejected by it.
Verified against the real file by mutation (see
`tests/README.md`): patching the seam's return line to the echo
form produced exactly 3 failures in 196; the file was restored
SHA-256-identical and the suite re-ran green.

## Verification

- Full suite on the final tree: **196 tests, OK** (176 pre-unit +
  20 new).
- Core byte-identity: SHA-256 of all 11 pre-existing
  `src/analytics/*.py` modules (the 10 core modules plus the
  first batch unit's `extensions.py`, still `87a3773b…`)
  identical before and after.
- Mutation drill: exactly 3 failures under the first-count-echo
  patch, restored and re-verified (raw output in
  `scratch/addition_gaps_mutation_run.txt`; pre-mutation copy at
  `scratch/extensions_addition.py.premutation`).
- No core change was needed; nothing in the addition executes an
  automation, signs or verifies a document, runs a workflow step,
  ships a client, opens a session, or computes a score.
