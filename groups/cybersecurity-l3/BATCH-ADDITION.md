# Final GAPS batch — second unit: Remainder Addition — Cybersecurity L3-adjacent

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Cybersecurity L3-adjacent (+2 forks)`**
(the +2 forks are Cisco Security Cloud for Government and XTec
AuthentX Cloud, added to this group by the remainder census; their
spec sheets' ADDENDUM §5 registered these gaps). Dispositions
follow `../../gaps-batch/DECISION.md`; platform-layer closures
follow `../../PLATFORM-LAYER.md`.

**Entry-count verification (as briefed):** the section holds 3
inventory entries (idx 620, 621, 622). Exactly **2 are open** —
idx 620 and idx 622 — matching the brief. The third, idx 621
("HSM as a Service…"), was already closed `re-scoped` under
PLATFORM-LAYER.md (the fork's FIPS 140-2 Level 3 HSM certification
is its platform property and does not transfer) and is **not part
of this unit**; it is named here so the count is reconciled, not
absorbed. No discrepancy.

Everything landed as ONE new module,
`src/cyber/extensions_addition.py` (`ExtensionAdditionStore`),
with denied attempts audit-recorded as
`extension_addition_denied`. The shared validators, the `count_by`
counting seam, and the fail-closed decorator are reused from
`cyber.extensions` (this package's own code; reuse stated in the
module docstring). All 9 pre-existing modules — the 8 inherited
core modules and the first batch unit's `extensions.py`
(`66a7e6e6…`) — are byte-identical (SHA-256 verified against the
pre-build record in `scratch/prebatch-addition-src.sha256`;
`store.py` still `1e58d852…`). No core extension was needed.
Tests: `tests/test_gaps_batch_addition.py`. Suite: **286 → 307**,
all passing.

The High apparatus binds the addition exactly as it bound the
first unit: writes are fail-closed on the core hash-chained audit
log (a failed audit append rolls back the record and its id
allocation, pinned by test); the separated auditor role is denied
every addition operation, reads included, while its core audit
duty works unchanged (the chain verifies `(True, None)` after
addition flows, pinned by test).

Category discipline holds on the whole surface: no extension
record, view, or summary computes a score (a recursive key scan
pins the absence of `score` / `band` / `confidence` keys — the
core's published deterministic finding and risk tables in
`cyber.store` remain the only scoring in the package and are not
re-implemented here); posture is counts and buckets only; every
count and latest value derives at read and is never a key on a
stored record; references are opaque tokens only (the founding
validator — no IPv4 literal, dotted hostname, URL, or whitespace —
tightened on the mail surface with an `@` refusal, so no field can
hold a mail address or any other PII); evidence-shaped data is
counts and labels only, never content.

## Per-entry disposition

### idx 620 — reference (stub-engine, as drafted)

> Firewall management & orchestration plane: NGFW policy / device management, zero-touch provisioning, AIOps policy analysis (Cisco)

Labeled reference implementation, in the first unit's SOAR form
carried to this plane (definitions and reported records, never
execution). The plane is an engine over external systems — it
manages NGFW devices, pushes policy to them, provisions them
zero-touch, and runs an AIOps analyzer — so its honest form here
is the reference surface, every record carrying
`reference_stub: True` and status `recorded`:

- `register_fw_device` (`fwd-`): a device under management by the
  external plane — opaque `device_ref`, `model_label` over
  {`asa`, `ftd`, `other`} (the ADDENDUM's NGFW ASA / FTD fleet).
  Nothing enrolls, configures, or contacts a device.
- `create_fw_policy` (`fwp-`): a policy definition bound to a
  recorded device, its `rules` held as the definition's own text
  (the playbook-steps precedent). The definition is never pushed
  to a device, applied, or enforced.
- `record_fw_provisioning` (`fwpr-`): a zero-touch provisioning
  outcome reported by the external plane, over
  {`completed`, `failed`, `cancelled`}. Nothing is provisioned.
- `record_fw_analysis` (`fwa-`): an AIOps policy-analysis result
  reported by the external plane — the analyzer's own label over
  {`conflict_reported`, `optimization_reported`,
  `no_issue_reported`, `other`}, recorded as source data. No
  policy is analyzed here and no score, confidence, or
  recommendation is computed from the label.
- `fw_device_view`: derives `policy_count`,
  `provisioning_count`, and `latest_provisioning_outcome` at read
  via the `latest_label` seam; the stored device record carries
  none of them, pinned by test.

Scope boundary recorded, not re-judged: this surface does not
duplicate the first unit's network-enforcement records
(`enforcement_points` / `enforcement_rules`) — those record the
declared configuration of enforcement points themselves; this
entry is the *management and orchestration plane above them*,
which is the engine the inventory triaged as a stub.

### idx 622 — built (build-extension, as drafted)

> Inline email security platform (Cisco; named separately from the phishing family's simulation / training content)

Built in records form, under the founding adjudication the first
unit applied to the DLP and network-enforcement families:
registries and ingestion records for a platform whose engines run
elsewhere. It is kept distinct from the phishing family's
simulation / training content (`cyber.extensions` campaigns): no
message is composed, sent, inspected, or stored here.

- `register_mail_gateway` (`mlg-`): a gateway registration —
  opaque `gateway_ref`, `deployment` over {`inline`, `api_based`,
  `other`} (the ADDENDUM's two deployment forms).
- `create_mail_policy` (`mlp-`): a declared policy record —
  `threat_category` over {`bec`, `phishing`, `malware`, `spam`,
  `qr_code`, `other`} (the ADDENDUM's named detection classes,
  quishing included) and `declared_action` over {`deliver`,
  `quarantine`, `block`, `tag`} recorded as data about the
  external platform's configuration. Recording it delivers,
  quarantines, blocks, and tags nothing.
- `record_mail_disposition` (`mld-`): one message disposition
  reported by the external platform — `disposition` over
  {`delivered`, `quarantined`, `blocked`, `tagged`} and
  `category` over the threat categories plus `clean`, recorded as
  the platform's own outcome for a message this substrate never
  saw. The message is named by an opaque `message_ref` only
  (founding ref validation plus the `@` refusal, pinned by test),
  and a disposition record is never scored.
- `mail_gateway_view`: derives `disposition_count`,
  `dispositions_by_disposition` (via the shared `count_by` seam),
  and `latest_disposition` (via `latest_label`) at read; the
  stored gateway record carries none of them, pinned by test.
- `mail_summary`: counts only — gateways, policies, dispositions,
  and the by-disposition / by-category distributions.

Privacy pin: no function on the addition surface can accept
message content, a subject, or a sender/recipient — enforced by a
signature test over every `ExtensionAdditionStore` method,
mirroring the first unit's log-pipeline pin.

## Re-judgments

None. The drafted split held on close reading against this
group's spec: idx 620 names an orchestration engine over external
systems and closes as the labeled reference implementation
(1 reference); idx 622 carries in the records form the founding
unit adjudicated for its sibling engine families (1 built).
Expected closure arithmetic for the parent: **2 entries closed —
1 built, 1 reference, no token overrides.** (idx 621 in the same
section stays as previously closed `re-scoped`; it is not part of
this unit's arithmetic.)

## Negative control

Fresh, for the new code: the latest-value seam
`latest_label` in `extensions_addition.py`, mutated to an
earliest-reading form (`records[0][key]`). Full suite under
mutation: **307 ran, exactly 3 failed**, all in
`test_gaps_batch_addition.py` (the firewall device view's latest
outcome, the mail gateway view's latest disposition, and the
control's canonical test). Restored from
`scratch/extensions_addition.py.premutation`, SHA-256 verified
identical (`8f4e3221…`), suite re-ran green. Full record in
`tests/README.md`; raw output in
`scratch/gaps_batch_addition_mutation_run.txt`.

## Honesty notes

- Nothing on this surface manages or provisions a firewall,
  pushes or applies a policy, analyzes a policy, or inspects,
  delivers, quarantines, blocks, or stores an email message; the
  firewall plane's records are labeled reference records and the
  mail platform's outcomes are reports recorded as data.
- Not covered (stays as it stands, not closed by this unit): the
  HSM as a Service entry (idx 621) remains closed `re-scoped`
  under PLATFORM-LAYER.md, and the High platform baseline gaps
  (IA-2(1)/(2)/IA-5, SC-13, SC-28, AU-11, AC-11/AC-12) remain
  closed in writing by the same decision.
