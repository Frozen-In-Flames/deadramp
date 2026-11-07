"""Final GAPS batch tests — Remainder Singleton 60 extension surface.

Pins the extension surface in ``src/events/extensions.py`` per
entry (see BATCH.md for the dispositions):

- Event delivery & presentation plane (reference): delivery
  session and join records carry the reference labels and the
  here-flags are False; join counts derive at read.
- Outreach delivery transport (built, records form): delivery
  records bound to core outreach, outcome verbatim,
  ``reference_transport: True``, nothing sent; summary counts
  derive at read.
- Matchmaking recommendation & pairing-suggestion engine
  (RE-JUDGED to reference): suggestion records are caller-stated,
  carry the reference labels, and no score/rank key exists.
- Live session facilitation (built): poll definitions + response
  records with counts derived at read by the seam; Q&A records
  with answered derived at read; chat records labeled transport.
- Speaker sourcing & booking (built): sourcing requests,
  candidate records (opaque speaker_ref only), booking records
  whose current state derives at read from append-only state
  records; the stored booking carries no state key.
- Identity provider (reference): the reference record carries
  ``identity_provider: False`` on its face.

Plus the cross-cutting pins: exact record key sets, a signature
scan (no identifier-shaped parameter, no ``**kwargs``), a
recursive no-score key scan, RBAC denial consuming no id, and
the fresh mutation-verified negative control on the poll-count
derivation seam.
"""

import inspect
import unittest

import events.extensions as extensions_module

from events.errors import NotFoundError, PermissionDenied, ValidationError
from events.extensions import EventsExtensions

from events_helpers import (ADMIN, MEMBER, SESS_ENDS, SESS_STARTS, VIEWER,
                            make_event, make_organizer, make_store,
                            make_vendors)

FORBIDDEN_PARAMS = {
    "name", "email", "phone", "attendee", "attendee_name",
    "person_name", "first_name", "last_name", "address",
    "score", "rank", "rating",
}


def _walk_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            keys.add(key)
            keys |= _walk_keys(sub)
    elif isinstance(value, list):
        for sub in value:
            keys |= _walk_keys(sub)
    return keys


def _fixture():
    store, audit = make_store()
    ext = EventsExtensions(store)
    organizer = make_organizer(store)
    vendors = make_vendors(store)
    event = make_event(store, organizer)
    session = store.create_session(ADMIN, event["id"], "webinar",
                                   "Opening webinar", SESS_STARTS, SESS_ENDS)
    return store, audit, ext, organizer, vendors, event, session


def _outreach(store, organizer, vendors, event):
    return store.record_outreach(MEMBER, organizer["id"], vendors[0]["id"],
                                 event["id"], "email", "Invitation")


def _round_with_participation(store, event, vendors):
    round_ = store.create_round(ADMIN, event["id"], ["cloud", "security"])
    participation = store.record_participation(
        MEMBER, round_["id"], vendors[0]["id"], ["cloud", "security"])
    return round_, participation


class DeliveryPlaneTests(unittest.TestCase):
    def test_delivery_session_is_labeled_reference(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        record = ext.create_delivery_session(ADMIN, session["id"],
                                             "webcast platform (label)")
        self.assertEqual(
            set(record),
            {"id", "session_id", "event_id", "platform_label",
             "reference_stub", "reference_transport", "streamed_here",
             "presented_here", "state", "created_by", "created_utc"})
        self.assertTrue(record["reference_stub"])
        self.assertTrue(record["reference_transport"])
        self.assertFalse(record["streamed_here"])
        self.assertFalse(record["presented_here"])
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertEqual(record["event_id"], session["event_id"])

    def test_join_records_and_derived_count(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        delivery = ext.create_delivery_session(ADMIN, session["id"], "p")
        view = ext.delivery_view(ADMIN, delivery["id"])
        self.assertEqual(view["join_count"], 0)
        join = ext.record_join(ADMIN, delivery["id"], "JOIN-0001")
        self.assertEqual(
            set(join),
            {"id", "delivery_session_id", "join_ref",
             "reference_transport", "admitted_here", "joined_here",
             "created_by", "created_utc"})
        self.assertFalse(join["admitted_here"])
        self.assertFalse(join["joined_here"])
        ext.record_join(ADMIN, delivery["id"], "JOIN-0002")
        view = ext.delivery_view(ADMIN, delivery["id"])
        self.assertEqual(view["join_count"], 2)

    def test_delivery_requires_core_session(self):
        _s, _a, ext, _o, _v, _e, _session = _fixture()
        with self.assertRaises(NotFoundError):
            ext.create_delivery_session(ADMIN, "ses-999", "p")


class OutreachDeliveryTests(unittest.TestCase):
    def test_delivery_record_bound_to_core_outreach(self):
        store, _a, ext, organizer, vendors, event, _session = _fixture()
        outreach = _outreach(store, organizer, vendors, event)
        record = ext.record_outreach_delivery(ADMIN, outreach["id"],
                                              "delivered (reported)")
        self.assertEqual(
            set(record),
            {"id", "outreach_id", "organizer_id", "vendor_id", "event_id",
             "channel", "outcome_label", "reference_transport", "sent_here",
             "delivered_here", "created_by", "created_utc"})
        self.assertEqual(record["channel"], "email")
        self.assertEqual(record["outcome_label"], "delivered (reported)")
        self.assertTrue(record["reference_transport"])
        self.assertFalse(record["sent_here"])
        self.assertFalse(record["delivered_here"])

    def test_delivery_summary_counts_derived(self):
        store, _a, ext, organizer, vendors, event, _session = _fixture()
        outreach = _outreach(store, organizer, vendors, event)
        ext.record_outreach_delivery(ADMIN, outreach["id"], "delivered")
        ext.record_outreach_delivery(ADMIN, outreach["id"], "bounced")
        ext.record_outreach_delivery(ADMIN, outreach["id"], "delivered")
        summary = ext.outreach_delivery_summary(ADMIN, outreach["id"])
        self.assertEqual(summary["delivery_count"], 3)
        self.assertEqual(summary["by_outcome_label"],
                         {"delivered": 2, "bounced": 1})

    def test_delivery_requires_core_outreach(self):
        _s, _a, ext, _o, _v, _e, _session = _fixture()
        with self.assertRaises(NotFoundError):
            ext.record_outreach_delivery(ADMIN, "out-999", "delivered")


class PairingSuggestionTests(unittest.TestCase):
    def test_suggestion_is_caller_stated_reference(self):
        store, _a, ext, _o, vendors, event, _session = _fixture()
        round_, participation = _round_with_participation(store, event,
                                                          vendors)
        record = ext.record_pairing_suggestion(
            ADMIN, round_["id"], participation["id"], "organizer pick")
        self.assertEqual(
            set(record),
            {"id", "round_id", "participation_id", "vendor_id",
             "rationale_label", "reference_stub", "suggested_here",
             "computed_here", "state", "created_by", "created_utc"})
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["suggested_here"])
        self.assertFalse(record["computed_here"])
        self.assertEqual(record["vendor_id"], vendors[0]["id"])
        self.assertEqual(record["rationale_label"], "organizer pick")

    def test_suggestion_requires_participation_of_the_round(self):
        store, _a, ext, _o, vendors, event, _session = _fixture()
        round_, _p = _round_with_participation(store, event, vendors)
        other = store.create_round(ADMIN, event["id"], ["cloud"])
        foreign = store.record_participation(
            MEMBER, other["id"], vendors[1]["id"], ["cloud"])
        with self.assertRaises(NotFoundError):
            ext.record_pairing_suggestion(ADMIN, round_["id"],
                                          foreign["id"], "x")


class FacilitationTests(unittest.TestCase):
    def test_poll_counts_derived_at_read(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        poll = ext.create_poll(ADMIN, session["id"], "Ready?",
                               ["yes", "no", "later"])
        self.assertEqual(
            set(poll),
            {"id", "session_id", "question", "options", "created_by",
             "created_utc"})
        view = ext.poll_view(ADMIN, poll["id"])
        self.assertEqual(view["counts"], [0, 0, 0])
        ext.record_poll_response(ADMIN, poll["id"], "RESP-1", 0)
        ext.record_poll_response(ADMIN, poll["id"], "RESP-2", 0)
        ext.record_poll_response(ADMIN, poll["id"], "RESP-3", 1)
        view = ext.poll_view(ADMIN, poll["id"])
        self.assertEqual(view["counts"], [2, 1, 0])
        self.assertEqual(view["response_total"], 3)
        self.assertNotIn("counts", poll)

    def test_poll_response_validation(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        poll = ext.create_poll(ADMIN, session["id"], "Q?", ["a", "b"])
        ext.record_poll_response(ADMIN, poll["id"], "RESP-1", 0)
        with self.assertRaises(ValidationError):
            ext.record_poll_response(ADMIN, poll["id"], "RESP-1", 1)
        with self.assertRaises(ValidationError):
            ext.record_poll_response(ADMIN, poll["id"], "RESP-2", 2)
        with self.assertRaises(ValidationError):
            ext.record_poll_response(ADMIN, poll["id"], "RESP-2", True)
        with self.assertRaises(ValidationError):
            ext.create_poll(ADMIN, session["id"], "Q?", ["only"])
        with self.assertRaises(ValidationError):
            ext.create_poll(ADMIN, session["id"], "Q?", ["a", "a"])

    def test_question_answered_derived_at_read(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        question = ext.record_question(ADMIN, session["id"], "ASK-1",
                                       "When is the next round?")
        view = ext.question_view(ADMIN, question["id"])
        self.assertEqual(view["answer_count"], 0)
        self.assertFalse(view["answered"])
        ext.record_answer(ADMIN, question["id"], "Next month.")
        view = ext.question_view(ADMIN, question["id"])
        self.assertEqual(view["answer_count"], 1)
        self.assertTrue(view["answered"])

    def test_chat_message_is_recorded_not_delivered(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        message = ext.record_chat_message(ADMIN, session["id"], "SEND-1",
                                          "Welcome, all.")
        self.assertEqual(
            set(message),
            {"id", "session_id", "sender_ref", "body",
             "reference_transport", "delivered_here", "created_by",
             "created_utc"})
        self.assertTrue(message["reference_transport"])
        self.assertFalse(message["delivered_here"])
        self.assertEqual(
            len(ext.list_chat_messages(ADMIN, session["id"])), 1)


class SpeakerTests(unittest.TestCase):
    def test_sourcing_and_candidate_records(self):
        _s, _a, ext, _o, _v, event, _session = _fixture()
        request = ext.create_sourcing_request(
            ADMIN, event["id"], "Keynote on procurement",
            ["Procurement", "FEDERAL", "procurement"])
        self.assertEqual(request["criteria_tags"],
                         ["procurement", "federal"])
        candidate = ext.record_speaker_candidate(
            ADMIN, request["id"], "SPK-0042", "Candidate (records label)")
        self.assertEqual(
            set(candidate),
            {"id", "sourcing_request_id", "speaker_ref", "label",
             "sourced_here", "created_by", "created_utc"})
        self.assertFalse(candidate["sourced_here"])
        self.assertEqual(candidate["speaker_ref"], "SPK-0042")

    def test_booking_state_derived_never_stored(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        booking = ext.create_booking(ADMIN, session["id"], "SPK-0042")
        self.assertEqual(
            set(booking),
            {"id", "session_id", "speaker_ref", "created_by",
             "created_utc"})
        view = ext.booking_view(ADMIN, booking["id"])
        self.assertIsNone(view["current_state"])
        ext.record_booking_state(ADMIN, booking["id"], "invited")
        view = ext.booking_view(ADMIN, booking["id"])
        self.assertEqual(view["current_state"], "invited")
        ext.record_booking_state(ADMIN, booking["id"], "confirmed")
        view = ext.booking_view(ADMIN, booking["id"])
        self.assertEqual(view["current_state"], "confirmed")
        self.assertEqual(view["state_count"], 2)


class IdentityProviderTests(unittest.TestCase):
    def test_idp_reference_record(self):
        _s, _a, ext, _o, _v, _e, _session = _fixture()
        record = ext.create_identity_provider_reference(
            ADMIN, "Embedding organization IdP (label)")
        self.assertEqual(
            set(record),
            {"id", "provider_label", "reference_stub", "identity_provider",
             "provided_here", "state", "created_by", "created_utc"})
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["identity_provider"])
        self.assertFalse(record["provided_here"])


class CrossCuttingTests(unittest.TestCase):
    def test_no_score_or_rank_key_anywhere(self):
        store, _a, ext, organizer, vendors, event, session = _fixture()
        outreach = _outreach(store, organizer, vendors, event)
        round_, participation = _round_with_participation(store, event,
                                                          vendors)
        delivery = ext.create_delivery_session(ADMIN, session["id"], "p")
        ext.record_join(ADMIN, delivery["id"], "JOIN-1")
        ext.record_outreach_delivery(ADMIN, outreach["id"], "delivered")
        ext.record_pairing_suggestion(ADMIN, round_["id"],
                                      participation["id"], "pick")
        poll = ext.create_poll(ADMIN, session["id"], "Q?", ["a", "b"])
        ext.record_poll_response(ADMIN, poll["id"], "RESP-1", 0)
        question = ext.record_question(ADMIN, session["id"], "ASK-1", "Q?")
        ext.record_answer(ADMIN, question["id"], "A.")
        ext.record_chat_message(ADMIN, session["id"], "SEND-1", "hi")
        request = ext.create_sourcing_request(ADMIN, event["id"], "T", [])
        ext.record_speaker_candidate(ADMIN, request["id"], "SPK-1", "L")
        booking = ext.create_booking(ADMIN, session["id"], "SPK-1")
        ext.record_booking_state(ADMIN, booking["id"], "invited")
        ext.create_identity_provider_reference(ADMIN, "IdP")
        surfaces = [
            ext.delivery_view(ADMIN, delivery["id"]),
            ext.list_outreach_deliveries(ADMIN),
            ext.outreach_delivery_summary(ADMIN),
            ext.list_pairing_suggestions(ADMIN),
            ext.poll_view(ADMIN, poll["id"]),
            ext.question_view(ADMIN, question["id"]),
            ext.list_chat_messages(ADMIN, session["id"]),
            ext.list_candidates(ADMIN),
            ext.booking_view(ADMIN, booking["id"]),
            ext.list_identity_provider_references(ADMIN),
            ext.extension_summary(ADMIN),
        ]
        for surface in surfaces:
            for key in _walk_keys(surface):
                self.assertNotIn("score", key)
                self.assertNotIn("rank", key)
                self.assertNotIn("rating", key)

    def test_signature_scan_no_identifier_params_no_kwargs(self):
        for name, method in inspect.getmembers(EventsExtensions,
                                               inspect.isfunction):
            if name.startswith("_"):
                continue
            for param in inspect.signature(method).parameters.values():
                self.assertNotEqual(param.kind, inspect.Parameter.VAR_KEYWORD,
                                    "%s takes **kwargs" % name)
                self.assertNotIn(param.name, FORBIDDEN_PARAMS,
                                 "%s has forbidden param %s" % (name,
                                                                 param.name))

    def test_smuggled_kwargs_raise_type_error(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        with self.assertRaises(TypeError):
            ext.record_join(ADMIN, "dly-1", "JOIN-1",
                            attendee_name="Real Name")
        with self.assertRaises(TypeError):
            ext.record_chat_message(ADMIN, session["id"], "SEND-1", "hi",
                                    email="a@example.com")

    def test_viewer_denied_and_failure_consumes_no_id(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        with self.assertRaises(PermissionDenied):
            ext.create_poll(VIEWER, session["id"], "Q?", ["a", "b"])
        with self.assertRaises(NotFoundError):
            ext.create_delivery_session(ADMIN, "ses-999", "p")
        delivery = ext.create_delivery_session(ADMIN, session["id"], "p")
        self.assertEqual(delivery["id"], "dly-1")
        poll = ext.create_poll(ADMIN, session["id"], "Q?", ["a", "b"])
        self.assertEqual(poll["id"], "pol-1")

    def test_extension_mutations_are_audited_with_ext_prefix(self):
        _s, audit, ext, _o, _v, _e, session = _fixture()
        ext.create_poll(ADMIN, session["id"], "Q?", ["a", "b"])
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_poll_create", actions)


def canonical_poll_counts(ext, session):
    """The poll suite's core expectation, stated once.

    Raises AssertionError when the poll view's derived counts do
    not assign each response to the option it recorded.
    """
    poll = ext.create_poll(ADMIN, session["id"], "Ready?",
                           ["yes", "no", "later"])
    ext.record_poll_response(ADMIN, poll["id"], "RESP-1", 0)
    ext.record_poll_response(ADMIN, poll["id"], "RESP-2", 0)
    ext.record_poll_response(ADMIN, poll["id"], "RESP-3", 1)
    view = ext.poll_view(ADMIN, poll["id"])
    assert view["counts"] == [2, 1, 0], (
        "counts are %s, expected [2, 1, 0]" % (view["counts"],))
    assert view["response_total"] == 3


def _mutant_poll_counts(responses, option_count):
    """Mutant: every response counts toward the FIRST option --
    the derivation no longer reads the recorded choice."""
    counts = [0] * option_count
    counts[0] = len(responses)
    return counts


class PollCountNegativeControlTests(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_seam(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        canonical_poll_counts(ext, session)

    def test_canonical_check_fails_on_the_mutant(self):
        _s, _a, ext, _o, _v, _e, session = _fixture()
        original = extensions_module._derive_poll_counts
        extensions_module._derive_poll_counts = _mutant_poll_counts
        try:
            with self.assertRaises(AssertionError):
                canonical_poll_counts(ext, session)
        finally:
            extensions_module._derive_poll_counts = original


ORACLE_EXPECTED = (
    "External drill (patch _derive_poll_counts in "
    "src/events/extensions.py to the all-first-option mutant, "
    "re-run the suite, restore): exactly 2 failures -- "
    "test_gaps_batch.FacilitationTests."
    "test_poll_counts_derived_at_read and test_gaps_batch."
    "PollCountNegativeControlTests."
    "test_canonical_check_passes_on_the_real_seam -- then the "
    "file restored byte-identical (SHA-256 verified) and the "
    "full suite green again. Recorded in tests/README.md and "
    "scratch/gaps-batch-mutation-run.txt."
)

if __name__ == "__main__":
    unittest.main()
