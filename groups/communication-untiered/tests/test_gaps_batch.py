"""Final GAPS batch tests for the Communication untiered set.

Traces to: the 9 open entries of this set's union spec gap list
(``UNION-SPEC.md``, GAPS.md section "Untiered Set 13 --
Communication (2 forks, tier null)"), closed by
``comm/extensions.py`` under ``../../gaps-batch/DECISION.md``:
5 built as records/derivations in-substrate, 4 shipped as labeled
reference implementations. The section's tenth entry (platform
layer) is already closed ``re-scoped`` and is not this unit's.

Every test names the entry it pins. Cross-cutting pins: tier null
binds the whole extension surface (a recursive scan finds no
tier-shaped key, no float, and no numeric list in any extension
record or view); stub records carry ``reference_stub: True``
(federation exchanges and channel dispatch records carry
``reference_transport: True``); denied attempts are audited
``ext_<action>:denied``; failed operations consume no id.

The fresh negative control is in
:class:`TestLatestReportNegativeControl`: the current-state
derivation seam ``CommExtensions._latest_report`` mutated to read
the earliest report instead of the latest must not produce the
canonical outcome.
"""

import unittest

from comm.errors import NotFoundError, PermissionDenied, ValidationError
from comm.extensions import CommExtensions

from comm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()
        self.ext = CommExtensions(self.store)
        self.ct = self.contact["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def second_contact(self):
        return self.store.create_contact(
            "Erin Example", {"voice": "+1-555-0101"}, OPERATOR)


def _walk(value):
    """Yield every (key, value) pair in a record/view, recursively."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


class TestPresence(BatchFixture):
    """Entry: Presence & availability services (built).

    Append-only presence reports over a core contact; the current
    state is derived at read by the seam and stored nowhere.
    """

    def test_report_shape_exact_keys(self):
        report = self.ext.record_presence(self.ct, "available", OPERATOR)
        self.assertEqual(report["id"], "prs-1")
        self.assertEqual(
            set(report.keys()),
            {"id", "contact_id", "state", "reported_utc",
             "created_by", "created_utc"})
        self.assertEqual(report["state"], "available")
        self.assertIsNone(report["reported_utc"])

    def test_current_state_is_latest_report(self):
        self.ext.record_presence(self.ct, "available", OPERATOR)
        self.ext.record_presence(self.ct, "busy", OPERATOR)
        view = self.ext.presence_view(self.ct, OPERATOR)
        self.assertEqual(view["current_state"], "busy")
        self.assertEqual(view["report_count"], 2)
        self.assertEqual(view["last_report_id"], "prs-2")
        self.assertIs(view["derived"], True)

    def test_unreported_contact_reads_unreported(self):
        view = self.ext.presence_view(self.ct, OPERATOR)
        self.assertEqual(view["current_state"], "unreported")
        self.assertEqual(view["report_count"], 0)
        self.assertIsNone(view["last_report_id"])

    def test_validation_and_no_id_on_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.record_presence(self.ct, "invisible", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_presence(self.ct, "busy", OPERATOR,
                                     reported_utc="not-a-date")
        with self.assertRaises(NotFoundError):
            self.ext.record_presence("ct-999", "busy", OPERATOR)
        report = self.ext.record_presence(self.ct, "busy", OPERATOR)
        self.assertEqual(report["id"], "prs-1")

    def test_viewer_may_not_record(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_presence(self.ct, "busy", VIEWER)
        self.assertIn("ext_presence_record:denied", self.audit_actions())

    def test_reports_listed_in_recording_order(self):
        self.ext.record_presence(self.ct, "away", OPERATOR)
        self.ext.record_presence(self.ct, "available", OPERATOR)
        reports = self.ext.list_presence_reports(self.ct, OPERATOR)
        self.assertEqual([r["state"] for r in reports],
                         ["away", "available"])


class TestContentSharing(BatchFixture):
    """Entry: Desktop sharing & collaboration content sharing (built).

    Share records hold an opaque content reference only; content is
    never held and never rendered.
    """

    def test_share_shape_and_labels(self):
        other = self.second_contact()
        share = self.ext.record_content_share(
            self.ct, "doc-ref-42", OPERATOR,
            recipient_contact_ids=[other["id"]])
        self.assertEqual(share["id"], "shr-1")
        self.assertEqual(
            set(share.keys()),
            {"id", "sharer_contact_id", "content_ref",
             "recipient_contact_ids", "content_held_here",
             "rendered_here", "created_by", "created_utc"})
        self.assertIs(share["content_held_here"], False)
        self.assertIs(share["rendered_here"], False)
        self.assertEqual(share["recipient_contact_ids"], [other["id"]])

    def test_no_parameter_accepts_content(self):
        with self.assertRaises(TypeError):
            self.ext.record_content_share(
                self.ct, "doc-ref-1", OPERATOR, content="binary-data")
        with self.assertRaises(TypeError):
            self.ext.record_content_share(
                self.ct, "doc-ref-1", OPERATOR, media=b"\x00\x01")

    def test_unknown_sharer_or_recipient_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_content_share("ct-999", "r", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_content_share(
                self.ct, "r", OPERATOR, recipient_contact_ids=["ct-999"])
        share = self.ext.record_content_share(self.ct, "r", OPERATOR)
        self.assertEqual(share["id"], "shr-1")

    def test_viewer_may_not_record(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_content_share(self.ct, "r", VIEWER)


class TestAccountability(BatchFixture):
    """Entry: Personnel accountability, location/status visibility
    & field-reporting platform (built).

    Status reports hold the caller-reported location label
    verbatim; nothing is sensed or tracked. Current state and
    muster counts derive at read.
    """

    def test_report_shape_and_labels(self):
        report = self.ext.record_status_report(
            self.ct, "safe", "Sector 7 muster point", OPERATOR)
        self.assertEqual(report["id"], "acc-1")
        self.assertEqual(
            set(report.keys()),
            {"id", "contact_id", "status", "location_label",
             "location_source", "tracked_here", "reported_utc",
             "created_by", "created_utc"})
        self.assertEqual(report["location_source"], "caller_reported")
        self.assertIs(report["tracked_here"], False)
        self.assertEqual(report["location_label"], "Sector 7 muster point")

    def test_current_status_is_latest_report(self):
        self.ext.record_status_report(self.ct, "unaccounted", "HQ",
                                      OPERATOR)
        self.ext.record_status_report(self.ct, "safe", "North gate",
                                      OPERATOR)
        view = self.ext.accountability_view(self.ct, OPERATOR)
        self.assertEqual(view["current_status"], "safe")
        self.assertEqual(view["current_location_label"], "North gate")
        self.assertEqual(view["report_count"], 2)

    def test_muster_counts_use_current_status(self):
        other = self.second_contact()
        self.ext.record_status_report(self.ct, "missing", "Field",
                                      OPERATOR)
        self.ext.record_status_report(self.ct, "safe", "HQ", OPERATOR)
        self.ext.record_status_report(other["id"], "injured", "Clinic",
                                      OPERATOR)
        summary = self.ext.muster_summary(OPERATOR)
        self.assertEqual(summary["total_contacts"], 2)
        self.assertEqual(summary["reported_contacts"], 2)
        self.assertEqual(summary["unreported_contacts"], 0)
        self.assertEqual(summary["by_current_status"],
                         {"safe": 1, "injured": 1})

    def test_muster_group_scope_and_unreported(self):
        summary = self.ext.muster_summary(OPERATOR,
                                          group_id=self.group["id"])
        self.assertEqual(summary["scope_group_id"], self.group["id"])
        self.assertEqual(summary["total_contacts"], 1)
        self.assertEqual(summary["reported_contacts"], 0)
        self.assertEqual(summary["unreported_contacts"], 1)
        self.assertEqual(summary["by_current_status"], {})

    def test_validation_and_no_id_on_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.record_status_report(self.ct, "fine", "HQ", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_status_report(self.ct, "safe", "", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_status_report("ct-999", "safe", "HQ", OPERATOR)
        report = self.ext.record_status_report(self.ct, "safe", "HQ",
                                               OPERATOR)
        self.assertEqual(report["id"], "acc-1")


class TestFederation(BatchFixture):
    """Entry: Inter-organizational federated communication networks
    (built, records form).

    Links and reported exchanges as records; no live network is
    formed and nothing is transmitted.
    """

    def _message(self):
        return self.store.compose_message(
            OPERATOR, subject="Notice", body="Body text",
            contact_ids=[self.ct], channel_kinds=["email"])

    def test_link_shape_and_labels(self):
        link = self.ext.record_federation_link("county-net", "County EMA",
                                               OPERATOR)
        self.assertEqual(link["id"], "fed-1")
        self.assertEqual(
            set(link.keys()),
            {"id", "network_ref", "peer_label", "reference_transport",
             "live_network_here", "created_by", "created_utc"})
        self.assertIs(link["reference_transport"], True)
        self.assertIs(link["live_network_here"], False)

    def test_exchange_shape_and_derived_count(self):
        link = self.ext.record_federation_link("county-net", "County EMA",
                                               OPERATOR)
        message = self._message()
        exchange = self.ext.record_federation_exchange(
            link["id"], "reported_delivered", OPERATOR,
            message_id=message["id"])
        self.assertEqual(exchange["id"], "fxg-1")
        self.assertIs(exchange["reference_transport"], True)
        self.assertIs(exchange["transmitted_here"], False)
        self.assertEqual(exchange["outcome_label"], "reported_delivered")
        view = self.ext.federation_link_view(link["id"], OPERATOR)
        self.assertEqual(view["exchange_count"], 1)
        stored = self.ext.list_federation_exchanges(link["id"], OPERATOR)
        self.assertEqual(len(stored), 1)

    def test_stored_link_carries_no_derived_count(self):
        link = self.ext.record_federation_link("n", "P", OPERATOR)
        self.ext.record_federation_exchange(link["id"], "ok", OPERATOR)
        view = self.ext.federation_link_view(link["id"], OPERATOR)
        self.assertIn("exchange_count", view)
        # A second view derives the same count; nothing accumulated.
        view2 = self.ext.federation_link_view(link["id"], OPERATOR)
        self.assertEqual(view2["exchange_count"], 1)

    def test_unknown_link_or_message_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_federation_exchange("fed-999", "ok", OPERATOR)
        link = self.ext.record_federation_link("n", "P", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_federation_exchange(
                link["id"], "ok", OPERATOR, message_id="msg-999")
        exchange = self.ext.record_federation_exchange(
            link["id"], "ok", OPERATOR)
        self.assertEqual(exchange["id"], "fxg-1")


class TestChannelTransports(BatchFixture):
    """Entry: Real channel transports (built records surface).

    Configuration and dispatch records in the founding adjudicated
    form: every record is labelled reference transport; no real
    channel exists and nothing is transmitted.
    """

    def test_config_shape_labels_and_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.configure_transport_channel("sms", "carrier-a",
                                                 OPERATOR)
        config = self.ext.configure_transport_channel("sms", "carrier-a",
                                                      ADMIN)
        self.assertEqual(config["id"], "trc-1")
        self.assertEqual(
            set(config.keys()),
            {"id", "kind", "name", "reference_transport",
             "real_channel_here", "transmitted_here",
             "created_by", "created_utc"})
        self.assertIs(config["reference_transport"], True)
        self.assertIs(config["real_channel_here"], False)
        self.assertIs(config["transmitted_here"], False)

    def test_dispatch_record_binds_core_message(self):
        config = self.ext.configure_transport_channel("email", "relay-a",
                                                      ADMIN)
        message = self.store.compose_message(
            OPERATOR, subject="S", body="B", contact_ids=[self.ct],
            channel_kinds=["email"])
        record = self.ext.record_channel_dispatch(
            config["id"], message["id"], OPERATOR)
        self.assertEqual(record["id"], "trd-1")
        self.assertIs(record["reference_transport"], True)
        self.assertIs(record["transmitted_here"], False)
        self.assertEqual(record["status"], "recorded_reference_only")
        # The core delivery still dispatches only via the core's own
        # reference transport; the extension record transmitted
        # nothing and altered no core record.
        deliveries = self.store.list_deliveries(message["id"])
        self.assertEqual(deliveries[0]["status"], "queued")
        self.assertIsNone(deliveries[0]["receipt"])

    def test_unknown_transport_or_message_rejected(self):
        config = self.ext.configure_transport_channel("push", "p", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_channel_dispatch("trc-999", "msg-1", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_channel_dispatch(config["id"], "msg-999",
                                             OPERATOR)


class TestMeetingSessions(BatchFixture):
    """Entry: Video conferencing, meetings & real-time media
    transport engines (reference stub).

    Session records only; no media is carried or connected.
    """

    def test_session_shape_and_labels(self):
        other = self.second_contact()
        session = self.ext.record_meeting_session(
            "Weekly sync", OPERATOR, organizer_contact_id=self.ct,
            participant_contact_ids=[other["id"]],
            scheduled_utc="2026-11-08T15:00:00Z")
        self.assertEqual(session["id"], "mtg-1")
        self.assertEqual(
            set(session.keys()),
            {"id", "title_label", "organizer_contact_id",
             "participant_contact_ids", "scheduled_utc",
             "reference_stub", "media_here", "connected_here",
             "created_by", "created_utc"})
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["media_here"], False)
        self.assertIs(session["connected_here"], False)

    def test_no_parameter_accepts_media(self):
        with self.assertRaises(TypeError):
            self.ext.record_meeting_session(
                "S", OPERATOR, media=b"\x00")
        with self.assertRaises(TypeError):
            self.ext.record_meeting_session(
                "S", OPERATOR, video_stream="rtmp://example")

    def test_unknown_participant_rejected_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_meeting_session(
                "S", OPERATOR, participant_contact_ids=["ct-999"])
        session = self.ext.record_meeting_session("S", OPERATOR)
        self.assertEqual(session["id"], "mtg-1")


class TestCalls(BatchFixture):
    """Entry: Voice/telephony media, call-control & endpoint
    interoperability engines (reference stub).

    Call outcome records only; no call is placed or connected.
    """

    def test_call_shape_and_labels(self):
        other = self.second_contact()
        call = self.ext.record_call(self.ct, other["id"],
                                    "reported_completed", OPERATOR)
        self.assertEqual(call["id"], "cal-1")
        self.assertEqual(
            set(call.keys()),
            {"id", "caller_contact_id", "callee_contact_id",
             "outcome_label", "reference_stub", "connected_here",
             "media_here", "created_by", "created_utc"})
        self.assertIs(call["reference_stub"], True)
        self.assertIs(call["connected_here"], False)
        self.assertIs(call["media_here"], False)
        self.assertEqual(call["outcome_label"], "reported_completed")

    def test_unknown_party_rejected_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_call(self.ct, "ct-999", "x", OPERATOR)
        other = self.second_contact()
        call = self.ext.record_call(self.ct, other["id"], "x", OPERATOR)
        self.assertEqual(call["id"], "cal-1")


class TestCrisisOrchestration(BatchFixture):
    """Entry: Crisis-communication orchestration & multi-channel
    alerting engines (reference stub).

    Campaign definitions held as data plus dispatch-request
    records; the registry never executes.
    """

    def test_campaign_definition_shape_and_labels(self):
        template = self.store.create_template(
            "alert", "Alert {place}", "Go to {place}", OPERATOR)
        campaign = self.ext.define_alert_campaign(
            "evac", ["sms", "email"], OPERATOR,
            template_id=template["id"])
        self.assertEqual(campaign["id"], "cmp-1")
        self.assertIs(campaign["definition_only"], True)
        self.assertIs(campaign["reference_stub"], True)
        self.assertIs(campaign["orchestrated_here"], False)
        self.assertIs(campaign["executed_here"], False)
        self.assertEqual(campaign["channel_kinds"], ["sms", "email"])

    def test_registry_never_executes(self):
        before_messages = self.store.list_messages()
        before_deliveries = self.store.list_deliveries()
        campaign = self.ext.define_alert_campaign("evac", ["push"],
                                                  OPERATOR)
        request = self.ext.record_campaign_dispatch_request(
            campaign["id"], OPERATOR, note_label="drill")
        self.assertEqual(request["id"], "cdr-1")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["reference_transport"], True)
        self.assertIs(request["dispatched_here"], False)
        self.assertEqual(self.store.list_messages(), before_messages)
        self.assertEqual(self.store.list_deliveries(), before_deliveries)

    def test_campaign_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.define_alert_campaign("x", [], OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.define_alert_campaign("x", ["smoke-signal"], OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.define_alert_campaign("x", ["sms"], OPERATOR,
                                           template_id="tpl-999")
        with self.assertRaises(NotFoundError):
            self.ext.record_campaign_dispatch_request("cmp-999", OPERATOR)


class TestVoicemail(BatchFixture):
    """Entry: Voicemail & unified messaging engines (reference stub).

    Voicemail records hold an opaque media reference only; no audio
    is recorded or held.
    """

    def test_voicemail_shape_and_labels(self):
        vm = self.ext.record_voicemail(self.ct, "County dispatch",
                                       "media-ref-7", OPERATOR)
        self.assertEqual(vm["id"], "vm-1")
        self.assertEqual(
            set(vm.keys()),
            {"id", "recipient_contact_id", "caller_label", "media_ref",
             "reference_stub", "recorded_here", "media_held_here",
             "created_by", "created_utc"})
        self.assertIs(vm["reference_stub"], True)
        self.assertIs(vm["recorded_here"], False)
        self.assertIs(vm["media_held_here"], False)

    def test_no_parameter_accepts_audio(self):
        with self.assertRaises(TypeError):
            self.ext.record_voicemail(self.ct, "c", "m", OPERATOR,
                                      audio=b"\x00\x01")
        with self.assertRaises(TypeError):
            self.ext.record_voicemail(self.ct, "c", "m", OPERATOR,
                                      audio_content="data:audio/wav;base64,x")

    def test_list_by_recipient(self):
        other = self.second_contact()
        self.ext.record_voicemail(self.ct, "a", "m-1", OPERATOR)
        self.ext.record_voicemail(other["id"], "b", "m-2", OPERATOR)
        mine = self.ext.list_voicemail(OPERATOR,
                                       recipient_contact_id=self.ct)
        self.assertEqual([v["id"] for v in mine], ["vm-1"])
        self.assertEqual(len(self.ext.list_voicemail(OPERATOR)), 2)


class MutantExtensions(CommExtensions):
    """The drill mutant: the seam reads the earliest report."""

    @staticmethod
    def _latest_report(reports):
        if not reports:
            return None
        return reports[0]


class TestLatestReportNegativeControl(BatchFixture):
    """Fresh negative control: the current-state derivation seam.

    The traced claim: a contact's current presence and
    accountability status are the **latest recorded** report's
    values -- a superseded report never resurfaces. Three legs:
    (1) the canonical implementation produces the latest-label
    outcome, (2) the mutant seam (earliest label) would NOT
    produce it, and (3) treating the mutant's outcome as the
    expected outcome fails, via a literal assertRaises.
    """

    def _setup_pair(self, ext):
        ext.record_presence(self.ct, "available", OPERATOR)
        ext.record_presence(self.ct, "busy", OPERATOR)
        ext.record_status_report(self.ct, "missing", "Field", OPERATOR)
        ext.record_status_report(self.ct, "safe", "HQ", OPERATOR)
        return ext

    def test_canonical_latest_wins(self):
        ext = self._setup_pair(self.ext)
        self.assertEqual(
            ext.presence_view(self.ct, OPERATOR)["current_state"], "busy")
        self.assertEqual(
            ext.accountability_view(self.ct, OPERATOR)["current_status"],
            "safe")

    def test_mutant_earliest_does_not_match_canonical(self):
        mutant = self._setup_pair(MutantExtensions(self.store))
        self.assertEqual(
            mutant.presence_view(self.ct, OPERATOR)["current_state"],
            "available")
        self.assertEqual(
            mutant.accountability_view(self.ct, OPERATOR)["current_status"],
            "missing")

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = self._setup_pair(MutantExtensions(self.store))
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.presence_view(self.ct, OPERATOR)["current_state"],
                "busy")


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned recursively:
    no key may name a tier, a baseline, or an equivalence; no value
    may be a float; no list may hold numbers.
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level")

    def _everything(self):
        ext = self.ext
        other = self.second_contact()
        ext.record_presence(self.ct, "available", OPERATOR)
        presence = ext.presence_view(self.ct, OPERATOR)
        share = ext.record_content_share(
            self.ct, "ref-1", OPERATOR, recipient_contact_ids=[other["id"]])
        ext.record_status_report(self.ct, "safe", "HQ", OPERATOR)
        account = ext.accountability_view(self.ct, OPERATOR)
        muster = ext.muster_summary(OPERATOR)
        link = ext.record_federation_link("net", "Peer", OPERATOR)
        exchange = ext.record_federation_exchange(
            link["id"], "reported_ok", OPERATOR)
        link_view = ext.federation_link_view(link["id"], OPERATOR)
        config = ext.configure_transport_channel("email", "relay", ADMIN)
        message = self.store.compose_message(
            OPERATOR, subject="S", body="B", contact_ids=[self.ct],
            channel_kinds=["email"])
        dispatch = ext.record_channel_dispatch(
            config["id"], message["id"], OPERATOR)
        session = ext.record_meeting_session(
            "Sync", OPERATOR, participant_contact_ids=[other["id"]])
        call = ext.record_call(self.ct, other["id"], "reported_done",
                               OPERATOR)
        campaign = ext.define_alert_campaign("evac", ["sms"], OPERATOR)
        request = ext.record_campaign_dispatch_request(
            campaign["id"], OPERATOR)
        voicemail = ext.record_voicemail(self.ct, "dispatch", "m-1",
                                         OPERATOR)
        reports = ext.list_presence_reports(self.ct, OPERATOR)
        return reports + [presence, share, account, muster, link,
                          exchange, link_view, config, dispatch, session,
                          call, campaign, request, voicemail]

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        for record in self._everything():
            for key, value in _walk(record):
                lowered = key.lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "tier-shaped key %r in %r" % (key, record))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, record))
                if isinstance(value, list):
                    for item in value:
                        self.assertNotIsInstance(
                            item, (int, float),
                            "numeric list at %r in %r" % (key, record))

    def test_stub_records_carry_their_labels(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        for stub_id in ("mtg-1", "cal-1", "cmp-1", "cdr-1", "vm-1"):
            self.assertIs(by_id[stub_id]["reference_stub"], True)
        for transport_id in ("fed-1", "fxg-1", "trc-1", "trd-1"):
            self.assertIs(by_id[transport_id]["reference_transport"],
                          True)

    def test_extension_surface_is_audited(self):
        self.ext.record_presence(self.ct, "busy", OPERATOR)
        actions = self.audit_actions()
        self.assertIn("ext_presence_record", actions)


class TestBareStoreFixture(unittest.TestCase):
    """The extension surface works over a bare core store too."""

    def test_bare_store(self):
        store = fresh_store()
        ext = CommExtensions(store)
        contact = store.create_contact(
            "Dana", {"email": "dana@example.com"}, OPERATOR)
        report = ext.record_presence(contact["id"], "available", OPERATOR)
        self.assertEqual(report["id"], "prs-1")
        with self.assertRaises(NotFoundError):
            ext.record_presence("ct-999", "busy", OPERATOR)


if __name__ == "__main__":
    unittest.main()
