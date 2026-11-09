"""Final GAPS batch tests, THIRD unit -- Health & Wellness L2
no-signal addition (CirrusMD, FR2220549818).

Pins the third-unit extension surface in
``src/health/extensions_nosignal.py``
(``HealthExtensionsNoSignal``, subclassing the second unit's
``HealthExtensionsAddition`` over the core ``HealthStore``): the
one open entry of the GAPS.md section "No-Signal Addition --
Health & Wellness L2 (CirrusMD, FR2220549818)" (see
``../BATCH-NOSIGNAL.md`` for the per-entry disposition), plus
cross-cutting pins -- the category's HARD PRIVACY RULE over the
whole no-signal surface (no diagnosis / clinical-note /
transcript / message-content / identifier-shaped key anywhere,
and forbidden fields cannot be smuggled in), derived-never-
stored values (channel and encounter current outcome labels and
counts), member scope, RBAC denials audited with the distinct
``extn_`` prefix and a ``:denied`` suffix, no id consumed by a
failed operation, and this unit's mutation-verified negative
control: the chat activity-ownership seam
``_check_chat_activity_belongs``, without which a chat encounter
could bind to ANOTHER participant's Core visit record.

Fixtures: ``make_store()`` (program "Diabetes Care", participant
under opaque ref "carol") plus a second participant (ref "erin")
where scope or ownership needs one.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError
from health.extensions_nosignal import HealthExtensionsNoSignal


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def _banned_keys(obj):
    """Keys that would break the founding privacy invariant.

    The HARD PRIVACY RULE: no diagnosis, no clinical free text,
    no transcript or message content, no direct identifier field
    in any shape. (Label keys such as ``transcript_held_here``
    state that a thing is NOT held and are not themselves the
    banned key.)
    """
    privacy = {
        "diagnosis", "note", "notes", "clinical_note", "clinical_notes",
        "name", "email", "phone", "ssn", "dob", "date_of_birth",
        "member_number", "address", "first_name", "last_name",
        "insurer", "insurer_name",
        "transcript", "message", "messages", "message_text",
        "chat_text", "conversation", "content",
        "risk_profile", "risk_score",
    }
    return {key for key in _all_keys(obj) if key.lower() in privacy}


class NoSignalFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.participant = make_store()
        self.ext = HealthExtensionsNoSignal(self.store)
        self.pid = self.participant["id"]
        self.prg = self.program["id"]
        self.other = self.store.create_participant("erin", ADMIN)

    def make_activity(self, participant_id=None, title="Chat visit"):
        return self.store.create_activity(
            participant_id or self.pid, title,
            "2026-03-01T15:00:00Z", ADMIN, program_id=self.prg)

    def make_channel(self, participant_id=None, channel_ref="chat-1"):
        return self.ext.create_chat_channel(
            participant_id or self.pid, channel_ref, CLINICIAN,
            program_id=self.prg)


class TestChatChannel(NoSignalFixture):
    """idx 968 -- chat-based virtual care channel (CirrusMD):
    channel definitions, encounter records, reported outcomes;
    the channel is never operated here."""

    def test_channel_record_shape_and_labels(self):
        channel = self.make_channel()
        self.assertEqual(channel["id"], "chc-1")
        self.assertEqual(channel["state"], "recorded_reference_only")
        self.assertTrue(channel["reference_stub"])
        self.assertTrue(channel["reference_transport"])
        self.assertFalse(channel["channel_operated_here"])
        self.assertFalse(channel["messages_delivered_here"])
        self.assertFalse(channel["routed_here"])
        self.assertFalse(channel["transcript_held_here"])
        self.assertFalse(channel["content_held_here"])

    def test_duplicate_channel_ref_refused(self):
        self.make_channel()
        with self.assertRaises(ValidationError):
            self.make_channel()

    def test_unknown_participant_and_program_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_chat_channel("par-99", "chat-1", CLINICIAN)
        with self.assertRaises(NotFoundError):
            self.ext.create_chat_channel(
                self.pid, "chat-1", CLINICIAN, program_id="prg-99")

    def test_encounter_binds_to_own_activity(self):
        channel = self.make_channel()
        activity = self.make_activity()
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN, activity_id=activity["id"],
            recorded_on="2026-03-01")
        self.assertEqual(encounter["id"], "che-1")
        self.assertEqual(encounter["activity_id"], activity["id"])
        self.assertEqual(encounter["participant_id"], self.pid)
        self.assertFalse(encounter["chat_conducted_here"])
        self.assertFalse(encounter["messages_exchanged_here"])
        self.assertFalse(encounter["transcript_held_here"])
        self.assertFalse(encounter["decided_here"])

    def test_encounter_refuses_other_participants_activity(self):
        channel = self.make_channel()
        foreign = self.make_activity(participant_id=self.other["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_chat_encounter(
                channel["id"], "enc-1", CLINICIAN,
                activity_id=foreign["id"])
        # The refused create consumed no id.
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-2", CLINICIAN)
        self.assertEqual(encounter["id"], "che-1")

    def test_unknown_channel_and_activity_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_chat_encounter("chc-99", "enc-1", CLINICIAN)
        channel = self.make_channel()
        with self.assertRaises(NotFoundError):
            self.ext.create_chat_encounter(
                channel["id"], "enc-1", CLINICIAN, activity_id="act-99")

    def test_duplicate_encounter_ref_refused(self):
        channel = self.make_channel()
        self.ext.create_chat_encounter(channel["id"], "enc-1", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_chat_encounter(channel["id"], "enc-1", CLINICIAN)

    def test_report_recorded_verbatim(self):
        channel = self.make_channel()
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN)
        report = self.ext.record_chat_encounter_report(
            encounter["id"], "guidance_provided", CLINICIAN,
            recorded_on="2026-03-01", reported_message_count=14)
        self.assertEqual(report["id"], "chr-1")
        self.assertEqual(report["outcome_label"], "guidance_provided")
        self.assertEqual(report["outcome_basis"], "platform_reported")
        self.assertEqual(report["reported_message_count"], 14)
        self.assertTrue(report["reference_transport"])
        self.assertFalse(report["measured_here"])
        self.assertFalse(report["delivered_here"])
        self.assertFalse(report["decided_here"])

    def test_bad_label_and_bad_count_refused(self):
        channel = self.make_channel()
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_chat_encounter_report(
                encounter["id"], "diagnosed", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_chat_encounter_report(
                encounter["id"], "responded", CLINICIAN,
                reported_message_count=True)
        with self.assertRaises(ValidationError):
            self.ext.record_chat_encounter_report(
                encounter["id"], "responded", CLINICIAN,
                reported_message_count=2.5)
        with self.assertRaises(ValidationError):
            self.ext.record_chat_encounter_report(
                encounter["id"], "responded", CLINICIAN,
                reported_message_count=-1)
        with self.assertRaises(NotFoundError):
            self.ext.record_chat_encounter_report(
                "che-99", "responded", CLINICIAN)

    def test_current_outcome_label_derived_at_read(self):
        channel = self.make_channel()
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN)
        view = self.ext.get_chat_encounter(encounter["id"], ADMIN)
        self.assertEqual(view["report_count"], 0)
        self.assertIsNone(view["current_outcome_label"])
        self.ext.record_chat_encounter_report(
            encounter["id"], "initiated", CLINICIAN)
        self.ext.record_chat_encounter_report(
            encounter["id"], "responded", CLINICIAN)
        view = self.ext.get_chat_encounter(encounter["id"], ADMIN)
        self.assertEqual(view["report_count"], 2)
        self.assertEqual(view["current_outcome_label"], "responded")
        # Nothing derived is stored on the raw records.
        stored_encounter = self.ext._chat_encounters[encounter["id"]]
        self.assertNotIn("current_outcome_label", stored_encounter)
        self.assertNotIn("report_count", stored_encounter)
        channel_view = self.ext.get_chat_channel(channel["id"], ADMIN)
        self.assertEqual(channel_view["encounter_count"], 1)
        self.assertEqual(channel_view["report_count"], 2)
        self.assertEqual(channel_view["current_outcome_label"], "responded")
        stored_channel = self.ext._chat_channels[channel["id"]]
        self.assertNotIn("encounter_count", stored_channel)
        self.assertNotIn("current_outcome_label", stored_channel)

    def test_summary_counts_only(self):
        channel = self.make_channel()
        other_channel = self.make_channel(
            participant_id=self.other["id"], channel_ref="chat-2")
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN)
        self.ext.record_chat_encounter_report(
            encounter["id"], "initiated", CLINICIAN)
        self.ext.record_chat_encounter_report(
            encounter["id"], "completed", CLINICIAN)
        summary = self.ext.chat_channel_summary(ADMIN)
        self.assertEqual(summary["channels"], 2)
        self.assertEqual(summary["encounters"], 1)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(summary["reports_by_outcome"],
                         {"initiated": 1, "completed": 1})
        self.assertFalse(summary["channel_operated_here"])
        self.assertFalse(summary["messages_delivered_here"])
        own = self.ext.chat_channel_summary(ADMIN, participant_id=self.pid)
        self.assertEqual(own["channels"], 1)
        self.assertEqual(other_channel["participant_id"], self.other["id"])

    def test_member_scope_on_channel_surface(self):
        self.make_channel()
        self.make_channel(participant_id=self.other["id"],
                          channel_ref="chat-2")
        own = self.ext.list_chat_channels(MEMBER)
        self.assertEqual([c["channel_ref"] for c in own], ["chat-1"])
        foreign = [c for c in self.ext.list_chat_channels(ADMIN)
                   if c["channel_ref"] == "chat-2"][0]
        with self.assertRaises(PermissionDenied):
            self.ext.get_chat_channel(foreign["id"], MEMBER)


class TestPrivacySurfaceNoSignal(NoSignalFixture):
    """Cross-cutting: the founding HARD PRIVACY RULE over the
    whole no-signal surface."""

    def _exercise_surface(self):
        channel = self.make_channel()
        activity = self.make_activity()
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN,
            activity_id=activity["id"], recorded_on="2026-03-01")
        self.ext.record_chat_encounter_report(
            encounter["id"], "responded", CLINICIAN,
            reported_message_count=6)
        return [
            self.ext.list_chat_channels(ADMIN),
            self.ext.list_chat_encounters(ADMIN),
            self.ext.list_chat_encounter_reports(ADMIN),
            self.ext.chat_channel_summary(ADMIN),
        ]

    def test_no_forbidden_key_anywhere_on_the_surface(self):
        for payload in self._exercise_surface():
            self.assertEqual(_banned_keys(payload), set())

    def test_forbidden_field_cannot_be_smuggled_as_kwarg(self):
        with self.assertRaises(TypeError):
            self.ext.create_chat_channel(
                self.pid, "chat-1", CLINICIAN, transcript="smuggled")
        channel = self.make_channel()
        with self.assertRaises(TypeError):
            self.ext.create_chat_encounter(
                channel["id"], "enc-1", CLINICIAN, message_text="smuggled")
        encounter = self.ext.create_chat_encounter(
            channel["id"], "enc-1", CLINICIAN)
        with self.assertRaises(TypeError):
            self.ext.record_chat_encounter_report(
                encounter["id"], "responded", CLINICIAN, note="smuggled")

    def test_denied_write_is_audited_with_denied_suffix(self):
        # The auditor holds no activity_write.
        with self.assertRaises(PermissionDenied):
            self.ext.create_chat_channel(self.pid, "chat-1", AUDITOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("extn_chat_channel_create:denied", actions)
        self.assertNotIn("extn_chat_channel_create", actions)


class _NoChatActivityOwnershipGuard(HealthExtensionsNoSignal):
    """Mutant: the chat activity-ownership seam neutralized."""

    def _check_chat_activity_belongs(self, activity, participant_id):
        return None


class TestChatActivityOwnershipNegativeControl(NoSignalFixture):
    """Negative control for this unit's fresh seam.

    A chat encounter bound to ANOTHER participant's Core
    activity (chat visit) record must be refused. The mutant
    subclass (ownership seam neutralized) would NOT produce
    that result; the canonical extension does. The same
    mutation was applied to the real module and the full suite
    run -- see tests/README.md for the verified failure count.
    """

    def _attempt_bind(self, ext):
        self._bind_attempts = getattr(self, "_bind_attempts", 0) + 1
        channel = ext.create_chat_channel(
            self.pid, "chat-x-%d" % self._bind_attempts, CLINICIAN)
        foreign = ext.store.create_activity(
            self.other["id"], "Foreign visit", "2026-03-01T15:00:00Z",
            ADMIN, program_id=self.prg)
        try:
            ext.create_chat_encounter(
                channel["id"], "enc-x-%d" % self._bind_attempts, CLINICIAN,
                activity_id=foreign["id"])
            return "accepted"
        except ValidationError:
            return "refused"

    def test_canonical_run_refuses_cross_participant_bind(self):
        self.assertEqual(self._attempt_bind(self.ext), "refused")

    def test_mutant_would_not_produce_the_refusal(self):
        mutant = _NoChatActivityOwnershipGuard(self.store)
        self.assertEqual(self._attempt_bind(mutant), "accepted")

    def test_guard_restored_refuses_again(self):
        self.assertEqual(self._attempt_bind(self.ext), "refused")


if __name__ == "__main__":
    unittest.main()
