# Final GAPS batch — Remainder Singleton 60 — Event Management L1

Unit: the 6 OPEN entries of GAPS.md section "Remainder Singleton
60 — Event Management L1 (1 fork, new category)" (inventory idx
705–710). Build: one new module, `src/events/extensions.py`
(`EventsExtensions` wrapping the core `EventsStore`), plus
`tests/test_gaps_batch.py`. Every pre-existing core module is
byte-identical (SHA-256 verified against the pre-build baseline);
the extension surface is records plus deterministic derivations
over the group's own records, per gaps-batch/DECISION.md.

Suite: 79 → 101 tests, all passing. Fresh mutation-verified
negative control: the poll-count derivation seam
`_derive_poll_counts` (see tests/README.md for the drill record:
exactly 2 failures under the all-first-option mutant, file
restored byte-identical).

## Per-entry dispositions

### idx 705 — reference (as drafted: stub-engine)

> Event delivery & presentation plane: webcast / streaming and the attendee join experience

Ships as a labeled reference implementation. Delivery-session
records bound to core session records (`dly-`) and join records
keyed by opaque `join_ref` only (`join-`) — there is no attendee
registry anywhere in this substrate and no field can hold a
name, email, or phone. Every record carries
`reference_stub: True` and `reference_transport: True`, with
`streamed_here` / `presented_here` / `admitted_here` /
`joined_here` all False: the webcast plane and the door act of
admission execute on live media systems outside this substrate,
so nothing is streamed, presented, or admitted. The one
derivation is a join count computed at read in `delivery_view`;
no count is stored.

### idx 706 — built (as drafted: build-extension)

> Outreach delivery transport (outreach records are Core; nothing is sent)

Built in records form under the entry's own bounding text.
Delivery records (`del-`) bound to core outreach records: the
channel is copied from the bound outreach record, the outcome is
a caller-reported label held verbatim, and the record carries
`reference_transport: True` with `sent_here` / `delivered_here`
False — the transport surface exists as records; nothing is
transmitted. `outreach_delivery_summary` derives deterministic
counts (total, and counts by outcome label) at read. Counts —
never scores.

### idx 707 — RE-JUDGED to reference (drafted: build-extension)

> Matchmaking recommendation & pairing-suggestion engine: the source carries no algorithm, scoring, ranking, or criteria vocabulary, so the build invents none — qualification in the Core is coverage over tags the organizer and vendors themselves recorded, and a recommendation engine is this gap, not a hidden feature

**Re-judgment under DECISION.md qualification 1, grounds:** the
entry's own text states the source carries no algorithm,
scoring, ranking, or criteria vocabulary and that the build
invents none. A recommendation engine's substance is exactly
that inference — proactively computing pairings beyond the
recorded-criteria coverage derivation the Core already performs.
Building the engine would require inventing criteria, which the
entry forbids; dressing caller-stated pairings up as a built
engine would misstate them. What ships instead is the honest
in-substrate form, labeled as reference: pairing-suggestion
records (`sug-`) in which a caller states that one of a round's
recorded participations be paired, with a caller-stated
rationale label held verbatim. Each record carries
`reference_stub: True` with `suggested_here` / `computed_here`
False and `state: recorded_reference_only`; the suggestion must
name a participation of the round (validated against the core's
records). No score, rank, or rating key exists anywhere in the
surface (pinned by recursive scan). The Core's coverage
derivation remains the only qualification rule, untouched.

### idx 708 — built (as drafted: build-extension)

> Live session facilitation: the chat / polling / Q&A tooling behind the prose adjective "interactive"

Built as facilitation records bound to core sessions. Poll
definitions (`pol-`) hold the question and option labels as
data; response records (`prs-`, one per opaque `respondent_ref`
per poll) hold the chosen option index, and per-option counts
are DERIVED at read by the single seam `_derive_poll_counts` —
no tally is ever stored. Q&A question records (`qa-`, opaque
`asker_ref`, question verbatim) and answer records (`ans-`);
a question's answer count and answered state derive at read.
Chat message records (`cht-`, opaque `sender_ref`, body
verbatim) form a recorded log whose delivery is transport, so
each carries `reference_transport: True` with
`delivered_here` False. Nothing is presented or moderated live;
the live plane is the delivery gap above, not this surface.

### idx 709 — built (as drafted: build-extension)

> Speaker sourcing & booking

Built as records. Sourcing requests (`src-`) record an event, a
topic label, and the organizer's criteria as normalized tags —
the request is recorded; sourcing itself is a human act outside
the substrate. Candidate records (`cand-`) name a speaker by
opaque `speaker_ref` only, with `sourced_here` False. Booking
records (`book-`) bind a core session to a `speaker_ref`; the
stored booking carries NO state key (pinned by test).
Booking-state records (`bst-`) are append-only caller-reported
state labels (invited / confirmed / declined, verbatim), and
`booking_view` derives the current state at read via
`_latest_state_label` over the state records in sequence order.

### idx 710 — reference (as drafted: stub-engine)

> Identity provider (demo identities are hooks, as everywhere in this repo)

Ships as a labeled reference record under PLATFORM-LAYER.md
decision 1: identity proofing, MFA, and any IdP/SSO engine stay
with the embedding organization. The record (`idp-`) declares
the reference and provides nothing — `reference_stub: True`,
`identity_provider: False`, `provided_here: False`,
`state: recorded_reference_only` on its face. Demo identities
remain hooks, not an IdP, exactly as the entry states.

## Cross-cutting

- Exact key sets pinned per record type; a signature scan pins
  that no extension method takes an identifier-shaped parameter
  (name / email / phone / attendee …) or `**kwargs`, and
  smuggled kwargs (`attendee_name=`, `email=`) raise TypeError.
- Recursive no-score key scan over every extension record, view,
  and summary: no key contains `score`, `rank`, or `rating`.
- RBAC enforced with the core's existing actions before any
  state change or id allocation; a denied or failed operation
  consumes no id (pinned: after a viewer denial and a
  not-found failure, the next delivery session is `dly-1`).
- Every successful extension mutation is audited on the core
  store's log with an `ext_`-prefixed action.
- No money shape anywhere, carried from the founding build: the
  fork's description names no fees or payments, so no extension
  record carries an amount field.
