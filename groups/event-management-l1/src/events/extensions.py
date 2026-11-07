"""Final GAPS batch extensions for the Event Management L1 build.

Clean-room, standard-library-only extensions for the 6 open
Extended entries of Remainder Singleton 60 (see ``BATCH.md`` in the
group directory for the per-entry disposition). This module is a
wrapper around :class:`EventsStore`; every core module is
untouched.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records. The substrate's founding decisions bind
this surface exactly as they bind the core: no record shape can
hold a person's name, email, or phone number (parties are opaque
references); there is no money field anywhere, because the fork's
description names no money; and nothing here is scored, ranked,
or rated -- counts are derived at read, never stored.

- The **event delivery & presentation plane** executes against
  live media systems outside this substrate, so it ships as
  labeled reference records: delivery-session records bound to
  core session records and join records keyed by opaque
  ``join_ref``, every record carrying ``reference_stub: True`` and
  ``reference_transport: True``, with ``streamed_here`` /
  ``presented_here`` / ``admitted_here`` all False. Nothing is
  streamed, presented, or admitted.
- The **outreach delivery transport** closes in records form
  under its own entry text ("outreach records are Core; nothing
  is sent"): delivery records bound to core outreach records,
  holding a caller-reported outcome label verbatim, each carrying
  ``reference_transport: True`` with ``sent_here`` /
  ``delivered_here`` False. Nothing is transmitted.
- The **matchmaking recommendation & pairing-suggestion engine**
  is RE-JUDGED to a labeled reference implementation (grounds in
  ``BATCH.md``): the entry's own text states the source carries
  no algorithm, scoring, ranking, or criteria vocabulary and the
  build invents none, and a recommendation engine's substance is
  the inference itself. What ships is pairing-suggestion
  RECORDS: a caller states a suggested pairing of a round with
  one of its participations, with a caller-stated rationale label
  held verbatim; each record carries ``reference_stub: True``
  with ``suggested_here`` / ``computed_here`` False. The core's
  coverage derivation is untouched and remains the only
  qualification rule.
- **Live session facilitation** closes as facilitation records
  bound to core sessions: poll definitions (question and option
  labels held as data) with response records whose counts are
  DERIVED at read by the single seam :func:`_derive_poll_counts`
  (no tally is ever stored); Q&A question and answer records,
  with a question's answered state derived at read; and chat
  message records -- a recorded log whose delivery is transport,
  so each message carries ``reference_transport: True`` with
  ``delivered_here`` False. Nothing is presented live.
- **Speaker sourcing & booking** closes as records: sourcing
  requests (topic label and caller-stated criteria tags),
  candidate records naming a speaker by opaque ``speaker_ref``
  only (``sourced_here`` False -- sourcing is a human act), and
  booking records bound to core sessions whose current state is
  DERIVED at read from append-only booking-state records by the
  seam :func:`_latest_state_label`; the stored booking record
  carries no state key.
- The **identity provider** entry closes as a labeled reference
  record under PLATFORM-LAYER.md decision 1 (identity stays with
  the embedding organization): ``reference_stub: True``,
  ``identity_provider: False``, ``provided_here: False`` on the
  record's face. Demo identities remain hooks, not an IdP.

Doctrines carried from the core: role permission is enforced for
User-like actors before any state change or id allocation, using
the core's existing actions, so a failed operation consumes no
id and changes nothing; every successful mutation is audited on
the core store's log with ``ext_``-prefixed actions; ids are
sequential per object type with fixed prefixes.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _tags(value, field):
    """Validate and normalize a tag list, mirroring the core
    store's rule: caller-stated strings, stripped lowercase,
    deduplicated preserving first-seen order."""
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of tag strings" % field)
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("%s must contain only non-empty strings" % field)
        tag = item.strip().lower()
        if tag not in result:
            result.append(tag)
    return result


def _options(value, field):
    """Validate a poll option list: at least two distinct
    non-empty label strings, held verbatim (stripped)."""
    if not isinstance(value, list) or len(value) < 2:
        raise ValidationError("%s must be a list of at least two options" % field)
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("%s must contain only non-empty strings" % field)
        label = item.strip()
        if label in result:
            raise ValidationError("%s must not repeat an option: %r" % (field, label))
        result.append(label)
    return result


def _derive_poll_counts(responses, option_count):
    """Poll-count derivation seam: the per-option response counts
    for a poll, computed from its response records alone.

    Pure function. Each response counts exactly once, toward the
    option it recorded. No tally is stored anywhere; the counts
    exist only in this derivation, so they cannot drift from the
    response records.
    """
    counts = [0] * option_count
    for response in responses:
        counts[response["option_index"]] += 1
    return counts


def _latest_state_label(state_records):
    """Latest-state seam: the state label of the most recently
    recorded booking-state record, or None when there are none.

    Booking state is append-only recorded fact; the CURRENT state
    is this derivation over the records in sequence order, never
    a field stored on the booking record.
    """
    if not state_records:
        return None
    return state_records[-1]["state_label"]


class EventsExtensions:
    """GAPS-batch extension surface wrapping an ``EventsStore``."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.Lock()
        self._delivery_sessions = {}
        self._joins = {}
        self._outreach_deliveries = {}
        self._suggestions = {}
        self._polls = {}
        self._poll_responses = {}
        self._questions = {}
        self._answers = {}
        self._chat_messages = {}
        self._sourcing_requests = {}
        self._candidates = {}
        self._bookings = {}
        self._booking_states = {}
        self._idp_references = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("no such %s: %r" % (what, record_id))
        return record

    def _core_session(self, actor, session_id):
        return self.store.get_session(actor, session_id)

    def _core_outreach(self, actor, outreach_id):
        for outreach in self.store.list_outreach(actor):
            if outreach["id"] == outreach_id:
                return outreach
        raise NotFoundError("no such outreach record: %r" % (outreach_id,))

    # -- event delivery & presentation plane (reference) -------------------

    def create_delivery_session(self, actor, session_id, platform_label):
        """Record a delivery/presentation session for a core
        session, as a labeled reference implementation: the
        webcast/streaming plane and the attendee join experience
        execute on live media systems outside this substrate, so
        what is recorded here is the reference record of such a
        session. Nothing is streamed or presented."""
        self._check_role(actor, "manage")
        session = self._core_session(actor, session_id)
        _text(platform_label, "platform_label")
        with self._lock:
            record = {
                "id": self._mint("dly-"),
                "session_id": session_id,
                "event_id": session["event_id"],
                "platform_label": platform_label,
                "reference_stub": True,
                "reference_transport": True,
                "streamed_here": False,
                "presented_here": False,
                "state": REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_sessions[record["id"]] = record
        self._record(actor, "ext_delivery_session_create", record["id"],
                     {"session_id": session_id})
        return dict(record)

    def get_delivery_session(self, actor, delivery_session_id):
        self._check_role(actor, "read")
        return dict(self._get(self._delivery_sessions,
                              delivery_session_id, "delivery session"))

    def list_delivery_sessions(self, actor, session_id=None):
        self._check_role(actor, "read")
        return [
            dict(r) for r in self._delivery_sessions.values()
            if session_id is None or r["session_id"] == session_id
        ]

    def record_join(self, actor, delivery_session_id, join_ref):
        """Record an attendee join against a delivery session, by
        opaque ``join_ref`` only -- there is no attendee registry
        and no field here can hold a name, email, or phone.
        Admission is a door act on a live system, not a records
        act: ``admitted_here`` is False."""
        self._check_role(actor, "manage")
        self._get(self._delivery_sessions, delivery_session_id,
                  "delivery session")
        _text(join_ref, "join_ref")
        with self._lock:
            record = {
                "id": self._mint("join-"),
                "delivery_session_id": delivery_session_id,
                "join_ref": join_ref,
                "reference_transport": True,
                "admitted_here": False,
                "joined_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._joins[record["id"]] = record
        self._record(actor, "ext_join_record", record["id"],
                     {"delivery_session_id": delivery_session_id})
        return dict(record)

    def list_joins(self, actor, delivery_session_id):
        self._check_role(actor, "read")
        self._get(self._delivery_sessions, delivery_session_id,
                  "delivery session")
        return [
            dict(r) for r in self._joins.values()
            if r["delivery_session_id"] == delivery_session_id
        ]

    def delivery_view(self, actor, delivery_session_id):
        """A delivery session with its join count DERIVED at read
        from the join records. No count is stored."""
        self._check_role(actor, "read")
        record = self._get(self._delivery_sessions,
                           delivery_session_id, "delivery session")
        view = dict(record)
        view["join_count"] = sum(
            1 for j in self._joins.values()
            if j["delivery_session_id"] == delivery_session_id
        )
        return view

    # -- outreach delivery transport (records form) -------------------------

    def record_outreach_delivery(self, actor, outreach_id, outcome_label):
        """Record a delivery of a core outreach record: the
        transport surface in records form, under the entry's own
        bound (nothing is sent). The outcome is a caller-reported
        label held verbatim; the record carries
        ``reference_transport: True`` and ``sent_here`` /
        ``delivered_here`` False."""
        self._check_role(actor, "outreach")
        outreach = self._core_outreach(actor, outreach_id)
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("del-"),
                "outreach_id": outreach_id,
                "organizer_id": outreach["organizer_id"],
                "vendor_id": outreach["vendor_id"],
                "event_id": outreach["event_id"],
                "channel": outreach["channel"],
                "outcome_label": outcome_label,
                "reference_transport": True,
                "sent_here": False,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._outreach_deliveries[record["id"]] = record
        self._record(actor, "ext_outreach_delivery_record", record["id"],
                     {"outreach_id": outreach_id})
        return dict(record)

    def list_outreach_deliveries(self, actor, outreach_id=None):
        self._check_role(actor, "read")
        return [
            dict(r) for r in self._outreach_deliveries.values()
            if outreach_id is None or r["outreach_id"] == outreach_id
        ]

    def outreach_delivery_summary(self, actor, outreach_id=None):
        """Deterministic counts over the delivery records,
        derived at read: total records and counts by
        caller-reported outcome label. Counts -- never scores."""
        self._check_role(actor, "read")
        by_outcome = {}
        total = 0
        for record in self._outreach_deliveries.values():
            if outreach_id is not None \
                    and record["outreach_id"] != outreach_id:
                continue
            total += 1
            by_outcome[record["outcome_label"]] = \
                by_outcome.get(record["outcome_label"], 0) + 1
        return {
            "outreach_id": outreach_id,
            "delivery_count": total,
            "by_outcome_label": by_outcome,
        }

    # -- matchmaking recommendation & pairing suggestions (reference) -------

    def record_pairing_suggestion(self, actor, round_id, participation_id,
                                  rationale_label):
        """Record a caller-stated pairing suggestion: that a
        round's recorded participation be paired, for a
        caller-stated rationale held verbatim. This is a labeled
        reference implementation of the recommendation engine
        (grounds in BATCH.md): the suggestion is the CALLER's,
        recorded -- ``suggested_here`` and ``computed_here`` are
        False, and no score, rank, or rating appears anywhere.
        The participation must be a recorded participation of the
        round."""
        self._check_role(actor, "matchmake")
        self.store.get_round(actor, round_id)
        participations = self.store.list_participations(actor, round_id)
        participation = None
        for candidate in participations:
            if candidate["id"] == participation_id:
                participation = candidate
                break
        if participation is None:
            raise NotFoundError(
                "no such participation in round %s: %r"
                % (round_id, participation_id))
        _text(rationale_label, "rationale_label")
        with self._lock:
            record = {
                "id": self._mint("sug-"),
                "round_id": round_id,
                "participation_id": participation_id,
                "vendor_id": participation["vendor_id"],
                "rationale_label": rationale_label,
                "reference_stub": True,
                "suggested_here": False,
                "computed_here": False,
                "state": REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._suggestions[record["id"]] = record
        self._record(actor, "ext_pairing_suggestion_record", record["id"],
                     {"round_id": round_id,
                      "participation_id": participation_id})
        return dict(record)

    def list_pairing_suggestions(self, actor, round_id=None):
        self._check_role(actor, "read")
        return [
            dict(r) for r in self._suggestions.values()
            if round_id is None or r["round_id"] == round_id
        ]

    # -- live session facilitation (records) --------------------------------

    def create_poll(self, actor, session_id, question, options):
        """Record a poll definition for a core session: the
        question and the option labels held as data. No tally is
        stored; counts derive at read from response records."""
        self._check_role(actor, "manage")
        self._core_session(actor, session_id)
        _text(question, "question")
        labels = _options(options, "options")
        with self._lock:
            record = {
                "id": self._mint("pol-"),
                "session_id": session_id,
                "question": question,
                "options": labels,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._polls[record["id"]] = record
        self._record(actor, "ext_poll_create", record["id"],
                     {"session_id": session_id})
        result = dict(record)
        result["options"] = list(labels)
        return result

    def record_poll_response(self, actor, poll_id, respondent_ref,
                             option_index):
        """Record one poll response: an opaque ``respondent_ref``
        and the index of the option it chose. One response per
        respondent per poll. Responses are records; presenting a
        live poll is the delivery plane, not this surface."""
        self._check_role(actor, "manage")
        poll = self._get(self._polls, poll_id, "poll")
        _text(respondent_ref, "respondent_ref")
        if isinstance(option_index, bool) \
                or not isinstance(option_index, int) \
                or option_index < 0 \
                or option_index >= len(poll["options"]):
            raise ValidationError(
                "option_index must be an integer in range: %r"
                % (option_index,))
        with self._lock:
            for existing in self._poll_responses.values():
                if existing["poll_id"] == poll_id \
                        and existing["respondent_ref"] == respondent_ref:
                    raise ValidationError(
                        "respondent %s already responded to poll %s"
                        % (respondent_ref, poll_id))
            record = {
                "id": self._mint("prs-"),
                "poll_id": poll_id,
                "respondent_ref": respondent_ref,
                "option_index": option_index,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._poll_responses[record["id"]] = record
        self._record(actor, "ext_poll_response_record", record["id"],
                     {"poll_id": poll_id})
        return dict(record)

    def poll_view(self, actor, poll_id):
        """A poll with its per-option counts DERIVED at read by
        the single seam :func:`_derive_poll_counts` from the
        response records alone. No tally is stored."""
        self._check_role(actor, "read")
        poll = self._get(self._polls, poll_id, "poll")
        responses = [
            r for r in self._poll_responses.values()
            if r["poll_id"] == poll_id
        ]
        counts = _derive_poll_counts(responses, len(poll["options"]))
        view = dict(poll)
        view["options"] = list(poll["options"])
        view["counts"] = counts
        view["response_total"] = len(responses)
        return view

    def list_polls(self, actor, session_id=None):
        self._check_role(actor, "read")
        return [self.poll_view(actor, p["id"])
                for p in self._polls.values()
                if session_id is None or p["session_id"] == session_id]

    def record_question(self, actor, session_id, asker_ref, question):
        """Record a Q&A question for a core session: an opaque
        ``asker_ref`` and the question text the caller states.
        Asking is recorded; live moderation is facilitation
        tooling on a live system, not this surface."""
        self._check_role(actor, "manage")
        self._core_session(actor, session_id)
        _text(asker_ref, "asker_ref")
        _text(question, "question")
        with self._lock:
            record = {
                "id": self._mint("qa-"),
                "session_id": session_id,
                "asker_ref": asker_ref,
                "question": question,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._questions[record["id"]] = record
        self._record(actor, "ext_question_record", record["id"],
                     {"session_id": session_id})
        return dict(record)

    def record_answer(self, actor, question_id, answer):
        """Record an answer to a recorded Q&A question."""
        self._check_role(actor, "manage")
        self._get(self._questions, question_id, "question")
        _text(answer, "answer")
        with self._lock:
            record = {
                "id": self._mint("ans-"),
                "question_id": question_id,
                "answer": answer,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._answers[record["id"]] = record
        self._record(actor, "ext_answer_record", record["id"],
                     {"question_id": question_id})
        return dict(record)

    def question_view(self, actor, question_id):
        """A Q&A question with its answer count and answered
        state DERIVED at read from the answer records. Neither
        is stored on the question."""
        self._check_role(actor, "read")
        question = self._get(self._questions, question_id, "question")
        answers = [
            a for a in self._answers.values()
            if a["question_id"] == question_id
        ]
        view = dict(question)
        view["answer_count"] = len(answers)
        view["answered"] = len(answers) > 0
        view["answers"] = [dict(a) for a in answers]
        return view

    def list_questions(self, actor, session_id=None):
        self._check_role(actor, "read")
        return [
            self.question_view(actor, q["id"])
            for q in self._questions.values()
            if session_id is None or q["session_id"] == session_id
        ]

    def record_chat_message(self, actor, session_id, sender_ref, body):
        """Record a chat message for a core session: an opaque
        ``sender_ref`` and the body the caller states. The log is
        a records surface; delivery to live participants is
        transport, so the record carries
        ``reference_transport: True`` and ``delivered_here``
        False."""
        self._check_role(actor, "manage")
        self._core_session(actor, session_id)
        _text(sender_ref, "sender_ref")
        _text(body, "body")
        with self._lock:
            record = {
                "id": self._mint("cht-"),
                "session_id": session_id,
                "sender_ref": sender_ref,
                "body": body,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._chat_messages[record["id"]] = record
        self._record(actor, "ext_chat_message_record", record["id"],
                     {"session_id": session_id})
        return dict(record)

    def list_chat_messages(self, actor, session_id):
        self._check_role(actor, "read")
        self._core_session(actor, session_id)
        return [
            dict(m) for m in self._chat_messages.values()
            if m["session_id"] == session_id
        ]

    # -- speaker sourcing & booking (records) --------------------------------

    def create_sourcing_request(self, actor, event_id, topic_label,
                                criteria_tags):
        """Record a speaker sourcing request for a core event: a
        topic label and the capability criteria the organizer
        states, as tags. Sourcing itself -- finding speakers --
        is a human act outside this substrate; what is recorded
        here is the request."""
        self._check_role(actor, "manage")
        self.store.get_event(actor, event_id)
        _text(topic_label, "topic_label")
        tags = _tags(criteria_tags, "criteria_tags")
        with self._lock:
            record = {
                "id": self._mint("src-"),
                "event_id": event_id,
                "topic_label": topic_label,
                "criteria_tags": tags,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sourcing_requests[record["id"]] = record
        self._record(actor, "ext_sourcing_request_create", record["id"],
                     {"event_id": event_id})
        result = dict(record)
        result["criteria_tags"] = list(tags)
        return result

    def record_speaker_candidate(self, actor, sourcing_request_id,
                                 speaker_ref, label):
        """Record a sourced speaker candidate against a sourcing
        request: the speaker named by opaque ``speaker_ref``
        only, with a records label. ``sourced_here`` is False --
        the sourcing happened outside this substrate; the
        candidate is its record."""
        self._check_role(actor, "manage")
        self._get(self._sourcing_requests, sourcing_request_id,
                  "sourcing request")
        _text(speaker_ref, "speaker_ref")
        _text(label, "label")
        with self._lock:
            record = {
                "id": self._mint("cand-"),
                "sourcing_request_id": sourcing_request_id,
                "speaker_ref": speaker_ref,
                "label": label,
                "sourced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._candidates[record["id"]] = record
        self._record(actor, "ext_speaker_candidate_record", record["id"],
                     {"sourcing_request_id": sourcing_request_id})
        return dict(record)

    def list_candidates(self, actor, sourcing_request_id=None):
        self._check_role(actor, "read")
        return [
            dict(c) for c in self._candidates.values()
            if sourcing_request_id is None
            or c["sourcing_request_id"] == sourcing_request_id
        ]

    def create_booking(self, actor, session_id, speaker_ref):
        """Record a speaker booking against a core session: the
        session and the speaker, by opaque ``speaker_ref`` only.
        The booking's state is NOT stored here -- it derives at
        read from booking-state records (see
        :meth:`record_booking_state`)."""
        self._check_role(actor, "manage")
        self._core_session(actor, session_id)
        _text(speaker_ref, "speaker_ref")
        with self._lock:
            record = {
                "id": self._mint("book-"),
                "session_id": session_id,
                "speaker_ref": speaker_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._bookings[record["id"]] = record
        self._record(actor, "ext_booking_create", record["id"],
                     {"session_id": session_id})
        return dict(record)

    def record_booking_state(self, actor, booking_id, state_label):
        """Append a booking-state record: a caller-reported state
        label (for example invited / confirmed / declined), held
        verbatim. State records are append-only; the booking's
        current state is the derivation over them, never an edit
        to the booking record."""
        self._check_role(actor, "manage")
        self._get(self._bookings, booking_id, "booking")
        _text(state_label, "state_label")
        with self._lock:
            record = {
                "id": self._mint("bst-"),
                "booking_id": booking_id,
                "state_label": state_label,
                "seq": self._counters["bst-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._booking_states[record["id"]] = record
        self._record(actor, "ext_booking_state_record", record["id"],
                     {"booking_id": booking_id})
        return dict(record)

    def booking_view(self, actor, booking_id):
        """A booking with its current state DERIVED at read by
        the seam :func:`_latest_state_label` from its state
        records in sequence order. The stored booking record
        carries no state key (pinned by test)."""
        self._check_role(actor, "read")
        booking = self._get(self._bookings, booking_id, "booking")
        states = sorted(
            (s for s in self._booking_states.values()
             if s["booking_id"] == booking_id),
            key=lambda s: s["seq"],
        )
        view = dict(booking)
        view["current_state"] = _latest_state_label(states)
        view["state_count"] = len(states)
        view["states"] = [dict(s) for s in states]
        return view

    def list_bookings(self, actor, session_id=None):
        self._check_role(actor, "read")
        return [
            self.booking_view(actor, b["id"])
            for b in self._bookings.values()
            if session_id is None or b["session_id"] == session_id
        ]

    # -- identity provider (reference) ----------------------------------------

    def create_identity_provider_reference(self, actor, provider_label):
        """Record the embedding organization's identity provider
        as a labeled reference: under PLATFORM-LAYER.md decision
        1, identity proofing, MFA, and any IdP/SSO engine stay
        with the embedding organization. This record declares the
        reference and provides nothing: ``identity_provider`` and
        ``provided_here`` are False on its face."""
        self._check_role(actor, "manage")
        _text(provider_label, "provider_label")
        with self._lock:
            record = {
                "id": self._mint("idp-"),
                "provider_label": provider_label,
                "reference_stub": True,
                "identity_provider": False,
                "provided_here": False,
                "state": REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._idp_references[record["id"]] = record
        self._record(actor, "ext_identity_provider_reference",
                     record["id"], {})
        return dict(record)

    def list_identity_provider_references(self, actor):
        self._check_role(actor, "read")
        return [dict(r) for r in self._idp_references.values()]

    # -- extension summary ------------------------------------------------------

    def extension_summary(self, actor):
        """Counts over the extension's own records, derived at
        read. Counts -- never scores."""
        self._check_role(actor, "read")
        return {
            "delivery_sessions": len(self._delivery_sessions),
            "joins": len(self._joins),
            "outreach_deliveries": len(self._outreach_deliveries),
            "pairing_suggestions": len(self._suggestions),
            "polls": len(self._polls),
            "poll_responses": len(self._poll_responses),
            "questions": len(self._questions),
            "answers": len(self._answers),
            "chat_messages": len(self._chat_messages),
            "sourcing_requests": len(self._sourcing_requests),
            "speaker_candidates": len(self._candidates),
            "bookings": len(self._bookings),
            "booking_states": len(self._booking_states),
            "identity_provider_references": len(self._idp_references),
        }
