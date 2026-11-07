# Final GAPS batch — Group 15, Contact Center L2

Unit: the 11 entries in GAPS.md under "Group 15 — Contact Center
L2 (5 forks)" (6 `build-extension`, 5 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 152–162). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
required re-judgment**: each fit its drafted disposition on a
close reading of this group's spec, in the forms stated below.

All extension code is in one new module,
`src/contact/extensions.py` (`ContactExtensions`, wrapping the
core `ContactStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified against
the pre-work baseline; `store.py` still `12709f80…`, the shipped
hash recorded in `tests/README.md`). Full suite: 107 tests
before, **155 tests after, OK** (48 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`
(the SLA seam drill: exactly 3 failures under mutation, all in
the batch's own tests).

Cross-cutting, per the group's doctrines:

- RBAC is enforced through the core `contact.access` matrix — the
  extension maps each operation onto an existing core action (the
  core action set is fixed; the mapping table is in the module
  docstring) and checks it before any state change or id
  allocation, following the core convention for plain-string
  actors. Denied attempts by User-like actors are recorded on the
  core audit log as `ext_<action>:denied` and every successful
  mutation as `ext_<action>`. If an audit write fails, the record
  insertion and its id roll back before the error propagates
  (pinned by test) — no extension record exists whose audit entry
  does not. The extension reads core records through the core's
  public API, plus two read-only accesses to the wrapped store's
  case records for SLA derivation (created/priority/status are
  inputs to the derivation; nothing is written back — pinned by
  the byte-identical core-case test).
- The pinned privacy discipline extends to every person-shaped
  reference on this surface: PAM subjects, risk subjects, and
  clearance subjects must be agents or contacts already in the
  core directory, and survey respondents must be core contacts —
  so the core's record shapes, which cannot hold a phone number,
  email address, or real identifier, govern them too. All other
  parties and systems are opaque `*_ref` strings. A recursive
  forbidden-key scan over all 22 extension record types (pinned
  by test) finds no phone/email/ssn-shaped key anywhere, and no
  score-shaped key on the risk, survey, or policy records.
- Derived values are derived at read and never stored: a PAM
  request's current state, a clearance case's current state,
  survey tallies, risk summaries, and SLA breach state under a
  recorded policy. Stored records carry no derived key; tests pin
  that.
- Nothing here executes against an external system. The five
  stub-engine families ship as labeled reference implementations:
  every record they create carries `reference_stub: True`
  (connector records also `reference_transport: True`), and no
  metric is collected, no call connects, no fraud is detected, no
  claim is adjudicated, and no model infers.
- The founding doctrine is not repealed: the core business-rule
  registry never executes, and nothing on this surface executes
  a rule either. The fraud family's rule records are definitions
  held as data in the extension's own registry, not registrations
  in the core registry.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `contact/extensions.py`) |
|---|---|---|
| PAM & Zero Trust enforcement engines (incl. just-in-time privileged access, session recording) (idx 152) | built | `create_access_request` (`pam-`, subject an existing core agent; target/justification opaque refs; the just-in-time window held as data; `granted_here: False`, `enforced_here: False` — recording a request grants nothing), `record_access_outcome` (`pamo-`, a reported grant state stored verbatim; current state derived at read from the latest outcome, never stored — pinned), `record_access_session` (`pams-`, an opaque session ref plus a reported state label; `content_held_here: False`, `monitored_here: False` — no session content exists here and nothing is monitored). Enforcement and identity stay with the embedding organization's PAM/IdP (`PLATFORM-LAYER.md` decision 1); this is the request log in front of them |
| Identity risk analytics & prescriptive recommendations (idx 153) | built | `record_risk_signal` (`risk-`, subject an existing core agent; the signal label stored verbatim as reported; `computed_here: False`), `record_recommendation` (`rec-`, a recommendation label held as data, optionally bound to a signal of the same agent — a cross-agent bind is refused; `computed_here` / `applied_here` False), `risk_summary` (counts by verbatim label derived at read). No numeric field exists on either shape: no risk score is computed, stored, or derivable here |
| Observability collection engines (collectors, metric collection, forecasting) (idx 154) | reference (stub-engine) | `register_collection_source` (`obs-`, opaque `source_ref`, the source kind as a caller label), `record_collection_report` (`obsr-`, reported counts — non-negative integers, booleans/floats rejected — and window labels stored verbatim) — `reference_stub: True`, `collected_here: False`, `forecast_computed_here: False` throughout; nothing is collected and no forecast is computed |
| Voice / telephony media & the callback connection engine (incl. ACD routing) (idx 155) | reference (stub-engine) | `record_telephony_session` (`tel-`, an opaque session ref plus a reported state, optionally linked to an existing core case/callback; `connected_here: False`, `media_here: False`), `record_routing_decision` (`route-`, an ACD decision stored as reported against an existing core queue; `routed_here: False`, pinned to leave queue membership untouched) — `reference_stub: True` throughout; no media exists in this build, nothing dials, and no record shape can hold a phone number (recursive scan) |
| Claims adjudication & fraud / waste / abuse detection engines (incl. rules execution; the core keeps a rule registry only) (idx 156) | reference (stub-engine) | `register_fraud_rule` (`fr-`, rule definitions held as data in the extension's own registry — name/case-type/condition/action text, validated like the core registry's; `executed_here: False`; admin-only like core rule writes), `record_fraud_finding` (`frf-`, a detection system's finding label stored verbatim against an existing core case; `detected_here: False`, `adjudicated_here: False`) — `reference_stub: True` throughout; a test pins that recording a finding leaves the core case byte-identical. No rule is executed and no claim is adjudicated |
| Personnel-security / facility-clearance management depth (idx 157) | built | `open_clearance_case` (`clr-`, subject an existing core agent or contact — the core directory itself rides a clearance level as an attribute, the SCCP pattern this entry extends; the clearance level recorded as a label; `adjudicated_here: False`), `record_clearance_outcome` (`clro-`, reported outcomes stored verbatim; current state derived at read from the latest outcome, never stored — pinned) |
| Integration connector engines (idx 158) | reference (stub-engine) | `register_connector` (`con-`, opaque `connector_ref`, the external system as a caller label), `record_connector_sync` (`conr-`, sync state and count stored verbatim as reported; `synced_here: False`) — `reference_stub: True` and `reference_transport: True` throughout; nothing connects or syncs |
| AI/ML models (1 claim) (idx 159) | reference (stub-engine) | `register_model` (`ml-`, opaque `model_ref`, capability as a caller label; `inference_here: False`, `trained_here: False`), `record_model_output` (`mlr-`, a reported output as a verbatim label plus an opaque output ref, optionally linked to an existing core case/alert) — `reference_stub: True` throughout; a test pins that recording an output creates no alert: the core's ingest paths remain the only way core records come to exist |
| Knowledge-base articles (0 of 5 claims; named absence) (idx 160) | built | `create_article` (`kb-` + first `kbrev-` revision), `revise_article` (appends a revision; unchanged fields carry forward; earlier revisions never change; no update or delete API), `get_article` / `list_articles` (current title/body and revision count derived at read from the latest revision — the stored article record holds only tags and provenance, pinned by an exact key-set test), `list_article_revisions` (the full append-only history), `search_articles` (literal substring search over current text — the registry-metadata pattern, not a search engine). The Customer Service groups' adjudicated form |
| Satisfaction / CSAT surveys (0 of 5 claims; named absence) (idx 161) | built | `create_survey` (`svy-`, instrument record with its scale as recorded integer terms, optionally bound to a core case), `record_survey_response` (`svr-`, respondent a contact already in the core directory by opaque id; rating validated against the instrument's recorded scale — integer only, booleans/floats refused — and stored verbatim, comment verbatim), `survey_tally` — response count, the full-scale distribution, and the mean as an **exact rational** (numerator/denominator over the recorded ratings, `method: exact_rational_mean_of_recorded_ratings`) derived at read; the stored survey record's exact key set is pinned — no tally or score key exists on any stored record. The Customer Service groups' adjudicated form |
| SLA policy engine (tiers, business-hour calendars, escalation; 0 of 5 claim SLA terms; the core derives breach from a per-case due time only) (idx 162) | built | `create_sla_policy` (`sla-`, per-priority resolution targets in minutes held as data — priorities must be core priorities; unknown/zero/negative/boolean/float terms refused at the boundary, no id consumed — plus a business-hour `calendar_ref` and an `escalation_ref` held as data: calendar arithmetic and escalation execution belong to the caller's systems, and nothing here escalates or notifies), `sla_case_view` and `sla_breach_report` — breach state derived at read from the core case record (created_utc, priority, status) against the recorded terms at the single seam `_is_breached_under_policy` (the batch's fresh negative control); terminal cases are never breached under a policy, uncovered priorities are never breached under it (their view reports `covered: False` with no target and no effective due time), and tests pin that policy views leave the core case record byte-identical. This derivation coexists with the core's own `due_at` derivation; neither replaces the other, and no sibling's SLA terms are invented — the terms are the operator's recorded data. The Customer Service L2 adjudicated form, extended with this entry's calendar/escalation references |

## Long-tail enumeration

Against the 18 families of `UNION-SPEC.md`'s function ranking:

| Spec family | Where it lands |
|---|---|
| Directory | Core (function 1) — the clearance entry's subjects live here; no extension needed for the registry itself |
| Queues | Core (function 2) — the telephony stub's routing records reference queues without changing them |
| Cases & lifecycle | Core (function 3) — the SLA entry derives policy breach over these records; findings/outputs reference them without changing them |
| Callback scheduling | Core (function 4) — telephony session records may link to callbacks; the connection engine is the telephony stub entry |
| Interaction records | Core (function 5) — no extension needed |
| Alert records | Core (function 6) — observability and AI/ML are the stub entries behind these records |
| Business-rule registry | Core (function 7); execution is not built anywhere — the fraud stub's definitions are data in the extension's own registry |
| Reports | Core (function 8) + the SLA breach report and risk summary derivations in this unit |
| Search | Core (function 9) + article search in the KB entry (registry-metadata pattern) |
| REST API | Core (function 10) — the extension surface is store-level only (below) |
| RBAC | Core (function 11); the extension maps onto the same matrix (module docstring) |
| Audit log | Core (function 12); every extension mutation and User-like denial lands on the same append-only log as `ext_*` / `ext_*:denied` entries |
| Identity, access control & Zero Trust | Core as substrate (RBAC); the products are the PAM entry (records form) and the identity-risk entry; IdP/PAM engines stay with the embedding organization (`PLATFORM-LAYER.md` decision 1) |
| Privileged access management & remote support sessions | The PAM entry |
| Risk assessment, detection & recommendations | The identity-risk entry (records form); detection engines proper are the fraud and observability stub entries |
| Monitoring & observability data collection | The observability stub entry |
| Voice & telephony channel | The telephony stub entry |
| Personnel, facility & clearance records management | Core (directory attributes) + the clearance entry's case depth |
| Claims & case processing | Core (case registry); adjudication is the fraud stub entry |
| Fraud, waste & abuse detection | The fraud stub entry |
| AI/ML capability | The AI/ML stub entry |
| Integrations & interoperability | The connector stub entry |
| Knowledge-base articles / CSAT surveys / SLA terms | Named absences at spec time (0 of 5 each); the KB, CSAT, and SLA entries in this unit |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Execution itself**, in every family that names it: no PAM
  grant is enforced, no rule is executed, no escalation fires, no
  notification is sent. The batch closes the records layer in
  front of those engines; the engines remain other systems'
  work, and the records say so on their face (`*_here: False`).
- **Business-hour calendar arithmetic**: the SLA entry holds a
  calendar *reference* as data, per the entry's own terms; the
  breach derivation is elapsed time against the recorded target
  (the Customer Service L2 adjudicated form), and computing
  business-time from a calendar definition is the caller's
  calendar system's work.
- **The section's platform-layer items** (multi-tenancy claimed
  in SCCP's prose, encryption at rest, TLS-when-configured,
  demo-identities-as-hooks) — not among the 11 entries; they
  stand on `PLATFORM-LAYER.md`, and no entry in this unit absorbs
  them.
- **Any sibling's domain engine as a product**: the PAM,
  observability, telephony, claims, and AI entries are records
  of those domains' shapes inside this substrate, not builds of
  BeyondTrust's, LogicMonitor's, Mindful's, or ClaimsXM's
  platforms. The claims those products make remain theirs.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
