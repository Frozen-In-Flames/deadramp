# Final GAPS batch — Untiered Set 17: Law Enforcement (2 forks, tier null)

**Unit.** The 9 open entries of GAPS.md section "Untiered Set 17
— Law Enforcement (2 forks, tier null)" (the set's union-spec
Extended functions, all nine ranked as extensions in
`UNION-SPEC.md`).

**Method.** Per `gaps-batch/DECISION.md`: extension code lands
as a NEW module in the owning group's `src/`; the founding core
modules stay byte-identical; stubs ship as labeled reference
implementations; if an entry does not fit its drafted
disposition on close reading of the owning set's spec, the unit
records the corrected disposition here and the parent closes
the entry with the matching token.

**Result.** 7 entries built as records in-substrate, 1 entry
shipped as a labeled reference implementation, 1 entry
re-judged to a written re-scope. Suite 91 → 133 tests, all
green; all seven founding core modules byte-identical to the
group README's accounting (re-verified after the build);
extension records registered: 14 kinds (operations, plans,
coordination messages, delivery receipts, location reports,
after-action reports, chain references, chain links, leads,
reported links, investigation requests, investigation results,
risk assessments, risk outcomes). One fresh mutation-verified
negative control (the chain-degree seam; exactly 3 failures
under the in/out swap), recorded in `tests/README.md`.

Every extension record is keyed by an opaque caller-supplied
`*_ref` string and holds metadata and SHA-256 digests only —
the set's hard privacy rule binds the new surface structurally:
no extension method has a parameter that can accept content,
message/report body text, query text, note text, a person's
name or identifier, an address value, or coordinates (passing
any such keyword raises `TypeError` before anything is recorded,
pinned by `tests/test_gaps_batch.py::TestPrivacyShapePins`), and
every record's exact key set is pinned. Tier null binds the
whole surface: no record or view carries a tier, baseline, or
equivalence key, a float, or a numeric list (recursive scan in
`TestTierNullAndShapeScan`), and no key anywhere names a score,
a rating, or a grade.

## Per-entry dispositions

| # | Entry (verbatim) | Drafted | Final | Token |
|---|---|---|---|---|
| 1 | Command-and-control & operational planning platform | build-extension | built | `built` |
| 2 | Real-time team coordination & encrypted messaging engines / real transports | build-extension | built | `built` |
| 3 | GPS mapping & location services | build-extension | built | `built` |
| 4 | After-action documentation & reporting engine | build-extension | built | `built` |
| 5 | Blockchain intelligence & multi-chain investigation graph engine | build-extension | built | `built` |
| 6 | All-source fusion & lead/identity resolution | build-extension | built | `built` |
| 7 | AI investigation models | build-extension | built | `built` |
| 8 | Operational risk-assessment tooling | stub-engine | reference | `reference` |
| 9 | Workspace multi-tenancy / platform layer | stub-engine | **re-judged: re-scoped in writing** | `re-scoped` |

## What was built (per entry)

1. **Command-and-control & operational planning platform —
   built.** Operation records (`opn-`, ref unique per matter)
   and plan records (`pln-`, optionally bound to an operation).
   Plans are definitions recorded as data; nothing is
   commanded, dispatched, or executed here
   (`commanded_here: False`, `orders_issued_here: False`,
   `definition_only: True`, `executed_here: False`). The
   operation view derives its message / location-report /
   after-action counts at read from the matter's own records;
   the stored operation carries no counts.
2. **Real-time team coordination & encrypted messaging engines
   / real transports — built, in the Communication adjudicated
   form.** Coordination message records (`msg-`) hold a channel
   reference and an optional body **digest** (SHA-256, validated
   64-hex; the method has no body/content/text parameter at
   all); delivery receipt records (`rcp-`) hold outcomes
   verbatim. Every message and receipt carries
   `reference_transport: True` and `transmitted_here: False`:
   the records describe deliveries; transmission happens on a
   real channel owned elsewhere. Encryption is never claimed:
   Pryme Infil's "encrypted messaging" is the fork's own claim
   about its own product (documented at prose weight in the
   union spec's Documented control claims); this build performs
   no cryptography (`encrypted_here: False` on every message),
   per `PLATFORM-LAYER.md` decisions 2–3 — a fork's validation
   posture does not transfer. The message view derives
   receipt_count / latest_outcome at read; the stored message
   carries neither.
3. **GPS mapping & location services — built.** Caller-reported
   location records (`loc-`): an opaque location ref, an
   optional opaque place ref, and an optional verbatim label,
   recorded exactly as the reporter stated them
   (`status: "recorded_report"`). The method has NO coordinate
   parameters — `latitude=`/`longitude=`/`coordinates=` raise
   `TypeError` — which is strictly inside what the set's spec
   allows (the category discipline excludes camera/sensor
   monitoring and real-time feeds by design, and the union spec
   claims no location data shape beyond reported status). The
   build senses nothing and tracks nothing
   (`tracked_here: False`, `sensed_here: False`).
4. **After-action documentation & reporting engine — built.**
   After-action report registrations (`aar-`): metadata plus an
   optional report digest (SHA-256). Reports are assembled by
   humans elsewhere; the substrate registers them and holds no
   report content (`content_held: False`, `generated_here:
   False`, `assembled_here: False`). The union spec bounds this
   explicitly: after-action documentation here is an operational
   function, not audit logging — the core's append-only audit
   log is a separate, already-implemented function and nothing
   in this entry extends it.
5. **Blockchain intelligence & multi-chain investigation graph
   engine — built.** Chain reference records (`chn-`, opaque
   chain/address references, network recorded as a verbatim
   label, `analyzed_here: False`) and reported link records
   (`lnk-`, both endpoints must be registered references in the
   matter, relation held verbatim). A link exists here only
   because someone reported it. The graph is never traversed
   and no attribution is computed (`reported_only: True`,
   `traversed_here: False`, `attribution_computed_here:
   False`); the reference view derives in/out/degree at read
   through the `_chain_degree` seam (the batch's fresh negative
   control), and the stored reference carries no degree.
6. **All-source fusion & lead/identity resolution — built.**
   Lead records (`led-`, optionally bound to a core source
   registration) and reported link records (`rlk-`, the other
   end an opaque ref, the relation a verbatim label). No
   resolution is performed and no identity is inferred
   (`resolved_here: False`, `identified_here: False`,
   `inferred_here: False`): a link exists only because someone
   reported it, and the record shapes carry no field that can
   hold a real name, case subject, party, address, or any
   person identifier — identity values are structurally
   unrepresentable, not merely unused. Fusion here means the
   lead registry and its reported links live beside the core's
   source/document/search/annotation records under one matter,
   not that anything is merged or matched. The lead view
   derives its reported-link count at read; recording links is
   proven by test to leave every core record byte-identical.
7. **AI investigation models — built (records form).**
   Investigation request records (`air-`, model held as a
   verbatim caller-supplied label, optionally bound to a lead)
   and investigation result records (`ars-`, the result an
   opaque reference plus an optional verbatim outcome label;
   `output_held: False`). No model runs here and no inference
   is performed (`inference_here: False` on both records).
   **Adjudication note:** this entry was drafted
   build-extension and is held as built rather than re-judged
   to reference, on the Data Management untiered precedent:
   there, vector-collection *definitions* (records machinery in
   the substrate) closed `built` while the stub-triaged AI
   entry closed `reference` because its substance was a running
   inference layer. Here the request/result registry is the
   same kind of records machinery — registration, binding,
   audit, and retrieval of requests and their opaque result
   references — while the inference itself is explicitly not
   claimed (`inference_here: False`). The parent may close this
   entry `reference` instead if it reads the entry's substance
   as the models rather than the registry; the code and tests
   are identical either way, and nothing on the surface changes.
8. **Operational risk-assessment tooling — reference, as
   drafted.** Risk assessment records (`rsk-`) and risk outcome
   records (`rko-`) carrying `reference_stub: True`,
   `assessed_here: False`, `status:
   "recorded_reference_only"`; outcomes are reported labels
   recorded verbatim (the citation-treatment discipline: never
   normalized, never scored, never aggregated). There is NO
   numeric score parameter and no key anywhere on the surface
   contains "score", "rating", or "grade" (signature
   `TypeError` on `score=`, `ValidationError` on a non-string
   outcome, recursive scan). The union spec bounds this entry
   explicitly: Pryme Infil's "risk assessments" is an
   operational service offered to agencies, recorded as such —
   it is not RA/CA control language and asserts no baseline
   posture.
9. **Workspace multi-tenancy / platform layer — re-judged to
   re-scoped in writing under `PLATFORM-LAYER.md` decision 6.**
   Grounds, on close reading of this set's spec: (a) the union
   spec claims NO records function for tenancy — the build is a
   single-tenant reference deployment (README), matter-scoped
   membership is the core's own already-implemented boundary,
   and "workspace-based multi-tenancy" appears for TRM Labs on
   GovCloud only inside the prose-tier IA sentence quoted in
   the Documented control claims; (b) decision 6 holds that a
   fork's hosting substrate / platform umbrella does not
   transfer, and multi-tenancy is a deployment property unless
   a group's spec claims a records function for it — this set's
   spec claims none, so there is nothing for the substrate to
   extend; (c) the entry's encryption parts are covered by
   decisions 2–3 (no FIPS-validated cryptography is claimed;
   TLS is deployment-layer). No code is built for this entry
   and no test pins it; the parent closes it `re-scoped`.

## Access mapping (recorded once)

The founding core's nine-action set is fixed, so the extension
maps its operations onto it (module docstring): operations and
plans under `matter_write`; coordination messages, receipts,
and location reports under `annotation_write` (records attached
to matter activity); after-action reports, chain references,
and chain links under `document_write` (document-class registry
entries); leads, reported links, and investigation requests /
results under `search_write` (investigation-class records);
risk assessments and outcomes under `citation_write` (verbatim
reported judgments, the citation-treatment discipline); reads
under `matter_read`; derived views under `report_read`. Both
founding boundaries are enforced on every operation: the role
via the core action set, and matter membership via the core
store (writes additionally require an open matter). Denials —
role or membership — are audited `ext_<action>:denied` on the
core audit log; successful mutations are audited
`ext_<action>` with the record kind.

## Not covered by this unit (explicit)

- The founding group's engine gaps — the legal corpora
  themselves, citation-validation engines, editorial
  enhancement systems, corpus search & relevance engines,
  document content storage/rendering — stay registered under
  the founding group's section; they are not this set's and
  are not covered here.
- The category-discipline exclusions — surveillance, facial
  recognition, predictive policing, real-time intelligence
  feeds, camera and sensor monitoring — are unclaimed-by-design
  in this category. They are not gaps, nothing in this unit
  builds them, and nothing here attributes them to either fork.
- Real message channels, real transports, real encryption, real
  location sensing/tracking, real chain traversal or
  attribution, real identity resolution, and real model
  inference are engines and deployments, not records; this unit
  builds the records and labels the boundary on every record.
- The extension surface is in-process only, like the Data
  Management untiered unit's: the founding HTTP service layer
  is unchanged and does not expose extension operations.
