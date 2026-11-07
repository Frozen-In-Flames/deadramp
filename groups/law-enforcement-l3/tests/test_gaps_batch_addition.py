"""Final GAPS batch tests, second unit, for Law Enforcement
L3-adjacent -- the TRAPWIRE remainder addition's own verticals.

Traces to: the 6 open Extended entries registered for the
remainder addition fork (TRAPWIRE Threat Detection and Analysis
System) in ``../ADDENDUM.md`` section 5 (GAPS.md section
"Remainder Addition -- Law Enforcement L3-adjacent (+1 fork)"),
closed by ``lawenf/extensions_addition.py`` under
``../../gaps-batch/DECISION.md``: 4 built as records
in-substrate (incident reporting & structured suspicious-
activity reporting; pattern analysis & analyst support;
originator-controlled cross-organizational information sharing;
mass warning & notification) and 2 shipped as labeled reference
implementations (threat detection & real-time alerting;
integration API & system-of-systems data integration), exactly
as drafted in the batch inventory -- no re-judgments
(``../BATCH-ADDITION.md``).

Every test names the entry it pins. Cross-cutting pins: the
hard privacy rule binds the whole addition surface (exact key
sets; no parameter can accept a report's text, a pattern's
description, a warning's message, a payload, a credential, or a
person's identifier -- ``TypeError`` by signature); no key
anywhere is score-shaped (nothing here scores, rates, ranks,
or predicts); reference records carry ``reference_stub: True``;
transport-shaped records carry ``reference_transport: True``;
extension mutations land on the core hash-chained audit log
audit-before-commit under ``ext2_`` action names (a failed
audit write commits nothing and consumes no id); the auditor
role is denied every addition operation; denied attempts are
audited ``ext2_<action>:denied``; failed operations consume no
id; derived values are derived at read and never stored.

The fresh negative control is in
:class:`TestAuthorizationNegativeControl`: the
current-authorization seam
``LawEnfExtensionsAddition._current_authorization_label``
mutated to read the first authorization event instead of the
latest must not produce the canonical current label.
"""

import hashlib
import os
import unittest

from lawenf.audit import AuditLog
from lawenf.errors import (
    AuditWriteError, NotFoundError, PermissionDenied, ValidationError,
)
from lawenf.extensions_addition import LawEnfExtensionsAddition

from lawenf_helpers import (
    ADMIN, AUDITOR, MEMBER, OUTSIDER, VIEWER, make_store,
)

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scratch")

REPORT_TEXT = "suspicious activity narrative, filed in the reporter's system"
REPORT_SHA256 = hashlib.sha256(REPORT_TEXT.encode("utf-8")).hexdigest()


def _scratch_file(name):
    path = os.path.join(SCRATCH, name)
    if os.path.exists(path):
        os.remove(path)
    return path


class MutantExtensionsAddition(LawEnfExtensionsAddition):
    """Negative-control mutant: the authorization seam reads the
    FIRST authorization event instead of the latest."""

    @staticmethod
    def _current_authorization_label(events):
        if events:
            return events[0]["event_label"]
        return "authorized_as_recorded"


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.matter = make_store()
        self.ext = LawEnfExtensionsAddition(self.store)
        self.mid = self.matter["id"]

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_report(self, ref="RPT-1", channel="web"):
        return self.ext.file_incident_report(
            self.mid, ref, channel, MEMBER, report_sha256=REPORT_SHA256)


class TestDetectionReference(AdditionFixture):
    """Entry: Threat detection & real-time alerting -- labeled
    reference implementation, as drafted: request and reported
    outcome records only; no detection or alerting capability
    exists here."""

    def test_request_shape_and_labels(self):
        req = self.ext.record_detection_request(
            self.mid, "DET-1", MEMBER, scope_label="perimeter reports")
        self.assertEqual(req["id"], "det-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "matter_id", "request_ref", "scope_label",
             "reference_stub", "detected_here", "alerted_here",
             "status", "created_by", "created_utc"})
        self.assertIs(req["reference_stub"], True)
        self.assertIs(req["detected_here"], False)
        self.assertIs(req["alerted_here"], False)
        self.assertEqual(req["status"], "recorded_reference_only")
        self.assertEqual(req["scope_label"], "perimeter reports")

    def test_outcome_shape_labels_and_verbatim(self):
        req = self.ext.record_detection_request(self.mid, "DET-1", MEMBER)
        out = self.ext.record_detection_outcome(
            self.mid, req["id"], "reported: match raised by network",
            MEMBER)
        self.assertEqual(out["id"], "dto-1")
        self.assertEqual(
            set(out.keys()),
            {"id", "matter_id", "request_id", "outcome_label",
             "reference_stub", "detected_here", "alerted_here",
             "created_by", "created_utc"})
        self.assertEqual(out["outcome_label"],
                         "reported: match raised by network")
        self.assertIs(out["reference_stub"], True)
        self.assertIs(out["detected_here"], False)
        self.assertIs(out["alerted_here"], False)

    def test_view_derives_count_and_latest_outcome(self):
        req = self.ext.record_detection_request(self.mid, "DET-1", MEMBER)
        self.ext.record_detection_outcome(self.mid, req["id"], "watching",
                                          MEMBER)
        self.ext.record_detection_outcome(self.mid, req["id"], "alerted",
                                          MEMBER)
        view = self.ext.detection_request_view(self.mid, req["id"], MEMBER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome"], "alerted")
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_detection_request(self.mid, req["id"], MEMBER)
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome", stored)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.record_detection_request(self.mid, "DET-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_detection_request(self.mid, "DET-1", MEMBER)
        req2 = self.ext.record_detection_request(self.mid, "DET-2", MEMBER)
        self.assertEqual(req2["id"], "det-2")

    def test_outcome_for_unknown_request_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_detection_outcome(self.mid, "det-999", "x",
                                              MEMBER)


class TestIncidentReports(AdditionFixture):
    """Entry: Incident reporting & structured suspicious-activity
    reporting -- built: filings registered as metadata + optional
    digest over the fork's three described channels; the report
    itself is never held."""

    def test_report_shape_and_labels(self):
        rep = self.make_report()
        self.assertEqual(rep["id"], "inc-1")
        self.assertEqual(
            set(rep.keys()),
            {"id", "matter_id", "report_ref", "channel",
             "report_sha256", "content_held", "status", "created_by",
             "created_utc"})
        self.assertEqual(rep["channel"], "web")
        self.assertEqual(rep["report_sha256"], REPORT_SHA256)
        self.assertIs(rep["content_held"], False)
        self.assertEqual(rep["status"], "filed")

    def test_all_three_channels_accepted(self):
        for i, channel in enumerate(("web", "mobile_field", "community")):
            rep = self.ext.file_incident_report(
                self.mid, "RPT-%s" % channel, channel, MEMBER)
            self.assertEqual(rep["channel"], channel)
            self.assertEqual(rep["id"], "inc-%d" % (i + 1))

    def test_unknown_channel_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.file_incident_report(self.mid, "RPT-X", "sensor_feed",
                                          MEMBER)

    def test_bad_digest_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.file_incident_report(
                self.mid, "RPT-1", "web", MEMBER, report_sha256="XYZ")
        rep = self.make_report()
        self.assertEqual(rep["id"], "inc-1")

    def test_list_filters_by_channel(self):
        self.make_report("RPT-1", "web")
        self.make_report("RPT-2", "community")
        self.assertEqual(
            len(self.ext.list_incident_reports(self.mid, actor=MEMBER)), 2)
        community = self.ext.list_incident_reports(
            self.mid, channel="community", actor=MEMBER)
        self.assertEqual(len(community), 1)
        self.assertEqual(community[0]["report_ref"], "RPT-2")

    def test_view_derives_analysis_count(self):
        rep = self.make_report()
        self.assertEqual(
            self.ext.incident_report_view(self.mid, rep["id"],
                                          MEMBER)["analysis_count"], 0)
        self.ext.record_pattern_analysis(
            self.mid, "ANA-1", MEMBER, incident_report_id=rep["id"])
        self.ext.record_pattern_analysis(self.mid, "ANA-2", MEMBER)
        view = self.ext.incident_report_view(self.mid, rep["id"], MEMBER)
        self.assertEqual(view["analysis_count"], 1)
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_incident_report(self.mid, rep["id"], MEMBER)
        self.assertNotIn("analysis_count", stored)


class TestPatternAnalysis(AdditionFixture):
    """Entry: Pattern analysis & analyst support -- built:
    analysis records and reported finding labels; no pattern is
    computed and no finding's text can enter."""

    def test_analysis_shape_and_labels(self):
        rep = self.make_report()
        ana = self.ext.record_pattern_analysis(
            self.mid, "ANA-1", MEMBER, incident_report_id=rep["id"],
            scope_label="perimeter reports, last 30 days")
        self.assertEqual(ana["id"], "ana-1")
        self.assertEqual(
            set(ana.keys()),
            {"id", "matter_id", "analysis_ref", "incident_report_id",
             "scope_label", "analyzed_here", "patterns_computed_here",
             "content_held", "status", "created_by", "created_utc"})
        self.assertIs(ana["analyzed_here"], False)
        self.assertIs(ana["patterns_computed_here"], False)
        self.assertIs(ana["content_held"], False)
        self.assertEqual(ana["scope_label"],
                         "perimeter reports, last 30 days")

    def test_analysis_binding_must_exist(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_pattern_analysis(
                self.mid, "ANA-1", MEMBER, incident_report_id="inc-999")

    def test_finding_shape_labels_and_verbatim(self):
        ana = self.ext.record_pattern_analysis(self.mid, "ANA-1", MEMBER)
        fin = self.ext.record_analysis_finding(
            self.mid, ana["id"], "RESULT-1", MEMBER,
            label="reported: recurring vehicle")
        self.assertEqual(fin["id"], "anf-1")
        self.assertEqual(
            set(fin.keys()),
            {"id", "matter_id", "analysis_id", "result_ref", "label",
             "analyzed_here", "computed_here", "content_held",
             "created_by", "created_utc"})
        self.assertEqual(fin["label"], "reported: recurring vehicle")
        self.assertIs(fin["analyzed_here"], False)
        self.assertIs(fin["computed_here"], False)

    def test_view_derives_finding_count_and_latest_label(self):
        ana = self.ext.record_pattern_analysis(self.mid, "ANA-1", MEMBER)
        self.ext.record_analysis_finding(self.mid, ana["id"], "R-1",
                                         MEMBER, label="first")
        self.ext.record_analysis_finding(self.mid, ana["id"], "R-2",
                                         MEMBER, label="second")
        view = self.ext.pattern_analysis_view(self.mid, ana["id"], MEMBER)
        self.assertEqual(view["finding_count"], 2)
        self.assertEqual(view["latest_finding_label"], "second")
        stored = self.ext.get_pattern_analysis(self.mid, ana["id"], MEMBER)
        self.assertNotIn("finding_count", stored)
        self.assertNotIn("latest_finding_label", stored)


class TestOriginatorSharing(AdditionFixture):
    """Entry: Originator-controlled cross-organizational
    information sharing -- built: authorization records and
    verbatim authorization events; the originator's control is
    recorded, never enforced here (no content exists here for
    control to operate over)."""

    def make_share(self):
        rep = self.make_report()
        return self.ext.record_share_authorization(
            self.mid, "OSH-1", "incident_report", rep["id"], "ORG-B",
            "ORG-A", MEMBER, scope_label="perimeter incidents")

    def test_authorization_shape_and_labels(self):
        share = self.make_share()
        self.assertEqual(share["id"], "osh-1")
        self.assertEqual(
            set(share.keys()),
            {"id", "matter_id", "share_ref", "target_kind", "target_id",
             "recipient_org_ref", "originator_ref", "scope_label",
             "reference_transport", "transmitted_here", "shared_here",
             "content_held", "control_enforced_here", "status",
             "created_by", "created_utc"})
        self.assertIs(share["reference_transport"], True)
        self.assertIs(share["transmitted_here"], False)
        self.assertIs(share["shared_here"], False)
        self.assertIs(share["content_held"], False)
        self.assertIs(share["control_enforced_here"], False)
        self.assertEqual(share["recipient_org_ref"], "ORG-B")
        self.assertEqual(share["originator_ref"], "ORG-A")

    def test_target_must_exist_and_kind_is_bounded(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_share_authorization(
                self.mid, "OSH-1", "incident_report", "inc-999", "ORG-B",
                "ORG-A", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_share_authorization(
                self.mid, "OSH-1", "document", "doc-1", "ORG-B", "ORG-A",
                MEMBER)

    def test_event_shape_and_labels(self):
        share = self.make_share()
        ev = self.ext.record_authorization_event(
            self.mid, share["id"], "granted by originator", MEMBER)
        self.assertEqual(ev["id"], "ose-1")
        self.assertEqual(
            set(ev.keys()),
            {"id", "matter_id", "share_id", "event_label",
             "reference_transport", "transmitted_here",
             "control_enforced_here", "created_by", "created_utc"})
        self.assertEqual(ev["event_label"], "granted by originator")
        self.assertIs(ev["reference_transport"], True)
        self.assertIs(ev["control_enforced_here"], False)

    def test_view_derives_current_label_from_latest_event(self):
        share = self.make_share()
        view = self.ext.share_authorization_view(self.mid, share["id"],
                                                 MEMBER)
        self.assertEqual(view["current_authorization_label"],
                         "authorized_as_recorded")
        self.assertEqual(view["authorization_event_count"], 0)
        self.ext.record_authorization_event(
            self.mid, share["id"], "granted by originator", MEMBER)
        self.ext.record_authorization_event(
            self.mid, share["id"], "revoked by originator", MEMBER)
        view = self.ext.share_authorization_view(self.mid, share["id"],
                                                 MEMBER)
        self.assertEqual(view["authorization_event_count"], 2)
        self.assertEqual(view["current_authorization_label"],
                         "revoked by originator")
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_share_authorization(self.mid, share["id"],
                                                  MEMBER)
        self.assertNotIn("current_authorization_label", stored)
        self.assertNotIn("authorization_event_count", stored)

    def test_analysis_target_accepted(self):
        ana = self.ext.record_pattern_analysis(self.mid, "ANA-1", MEMBER)
        share = self.ext.record_share_authorization(
            self.mid, "OSH-1", "pattern_analysis", ana["id"], "ORG-B",
            "ORG-A", MEMBER)
        self.assertEqual(share["target_kind"], "pattern_analysis")


class TestMassWarnings(AdditionFixture):
    """Entry: Mass warning & notification -- built: warning
    records and verbatim delivery reports; nothing is sent
    here."""

    def test_warning_shape_and_labels(self):
        wrn = self.ext.record_mass_warning(
            self.mid, "WRN-1", "all network member organizations", MEMBER)
        self.assertEqual(wrn["id"], "wrn-1")
        self.assertEqual(
            set(wrn.keys()),
            {"id", "matter_id", "warning_ref", "audience_label",
             "reference_transport", "sent_here", "distributed_here",
             "content_held", "status", "created_by", "created_utc"})
        self.assertEqual(wrn["audience_label"],
                         "all network member organizations")
        self.assertIs(wrn["reference_transport"], True)
        self.assertIs(wrn["sent_here"], False)
        self.assertIs(wrn["distributed_here"], False)
        self.assertIs(wrn["content_held"], False)

    def test_delivery_shape_labels_and_verbatim(self):
        wrn = self.ext.record_mass_warning(self.mid, "WRN-1", "network",
                                           MEMBER)
        rep = self.ext.record_warning_delivery(
            self.mid, wrn["id"], "reported: distributed to 41 endpoints",
            MEMBER)
        self.assertEqual(rep["id"], "wnr-1")
        self.assertEqual(
            set(rep.keys()),
            {"id", "matter_id", "warning_id", "outcome_label",
             "reference_transport", "sent_here", "created_by",
             "created_utc"})
        self.assertEqual(rep["outcome_label"],
                         "reported: distributed to 41 endpoints")
        self.assertIs(rep["sent_here"], False)

    def test_view_derives_count_and_latest_outcome(self):
        wrn = self.ext.record_mass_warning(self.mid, "WRN-1", "network",
                                           MEMBER)
        self.ext.record_warning_delivery(self.mid, wrn["id"], "queued",
                                         MEMBER)
        self.ext.record_warning_delivery(self.mid, wrn["id"], "delivered",
                                         MEMBER)
        view = self.ext.mass_warning_view(self.mid, wrn["id"], MEMBER)
        self.assertEqual(view["delivery_report_count"], 2)
        self.assertEqual(view["latest_outcome"], "delivered")
        stored = self.ext.get_mass_warning(self.mid, wrn["id"], MEMBER)
        self.assertNotIn("delivery_report_count", stored)
        self.assertNotIn("latest_outcome", stored)


class TestIntegrationReference(AdditionFixture):
    """Entry: Integration API & system-of-systems data
    integration -- labeled reference implementation, as drafted:
    connector definitions and reported exchange outcomes only;
    nothing connects and no data moves."""

    def test_connector_shape_and_labels(self):
        con = self.ext.record_integration_connector(
            self.mid, "INT-1", "LEGACY-RMS-REF", MEMBER,
            direction_label="inbound reports")
        self.assertEqual(con["id"], "int-1")
        self.assertEqual(
            set(con.keys()),
            {"id", "matter_id", "connector_ref", "system_ref",
             "direction_label", "reference_stub", "reference_transport",
             "connected_here", "data_moved_here", "status", "created_by",
             "created_utc"})
        self.assertIs(con["reference_stub"], True)
        self.assertIs(con["reference_transport"], True)
        self.assertIs(con["connected_here"], False)
        self.assertIs(con["data_moved_here"], False)
        self.assertEqual(con["status"], "recorded_reference_only")

    def test_exchange_shape_labels_and_verbatim(self):
        con = self.ext.record_integration_connector(
            self.mid, "INT-1", "LEGACY-RMS-REF", MEMBER)
        exc = self.ext.record_integration_exchange(
            self.mid, con["id"], "reported: sync completed by runtime",
            MEMBER)
        self.assertEqual(exc["id"], "ino-1")
        self.assertEqual(
            set(exc.keys()),
            {"id", "matter_id", "connector_id", "outcome_label",
             "reference_stub", "reference_transport", "connected_here",
             "data_moved_here", "created_by", "created_utc"})
        self.assertEqual(exc["outcome_label"],
                         "reported: sync completed by runtime")
        self.assertIs(exc["connected_here"], False)
        self.assertIs(exc["data_moved_here"], False)

    def test_view_derives_count_and_latest_outcome(self):
        con = self.ext.record_integration_connector(
            self.mid, "INT-1", "LEGACY-RMS-REF", MEMBER)
        self.ext.record_integration_exchange(self.mid, con["id"], "one",
                                             MEMBER)
        self.ext.record_integration_exchange(self.mid, con["id"], "two",
                                             MEMBER)
        view = self.ext.integration_connector_view(self.mid, con["id"],
                                                   MEMBER)
        self.assertEqual(view["exchange_count"], 2)
        self.assertEqual(view["latest_outcome"], "two")
        stored = self.ext.get_integration_connector(self.mid, con["id"],
                                                    MEMBER)
        self.assertNotIn("exchange_count", stored)
        self.assertNotIn("latest_outcome", stored)


class TestPrivacyShapePinsAddition(AdditionFixture):
    """The hard privacy rule, by signature: no addition method
    can accept a report's text, a pattern's description, a
    warning's message, a payload, a credential, an endpoint, or
    a person's identifier -- passing any such keyword raises
    TypeError before anything is recorded."""

    def test_content_shaped_kwargs_raise_type_error(self):
        rep = self.make_report()
        ana = self.ext.record_pattern_analysis(self.mid, "ANA-1", MEMBER)
        share = self.ext.record_share_authorization(
            self.mid, "OSH-1", "incident_report", rep["id"], "ORG-B",
            "ORG-A", MEMBER)
        wrn = self.ext.record_mass_warning(self.mid, "WRN-1", "network",
                                           MEMBER)
        con = self.ext.record_integration_connector(
            self.mid, "INT-1", "SYS-1", MEMBER)
        attempts = [
            lambda: self.ext.file_incident_report(
                self.mid, "RPT-9", "web", MEMBER, report_text="narrative"),
            lambda: self.ext.file_incident_report(
                self.mid, "RPT-9", "web", MEMBER, subject_name="a person"),
            lambda: self.ext.file_incident_report(
                self.mid, "RPT-9", "web", MEMBER, reporter_name="a name"),
            lambda: self.ext.record_detection_request(
                self.mid, "DET-9", MEMBER, report_content=b"bytes"),
            lambda: self.ext.record_detection_outcome(
                self.mid, "det-1", "ok", MEMBER, alert_text="text"),
            lambda: self.ext.record_pattern_analysis(
                self.mid, "ANA-9", MEMBER, pattern_text="description"),
            lambda: self.ext.record_analysis_finding(
                self.mid, ana["id"], "R-9", MEMBER, finding_text="text"),
            lambda: self.ext.record_share_authorization(
                self.mid, "OSH-9", "incident_report", rep["id"], "ORG-B",
                "ORG-A", MEMBER, recipient_name="a person"),
            lambda: self.ext.record_authorization_event(
                self.mid, share["id"], "ok", MEMBER, note_text="a note"),
            lambda: self.ext.record_mass_warning(
                self.mid, "WRN-9", "network", MEMBER,
                message_text="evacuate"),
            lambda: self.ext.record_warning_delivery(
                self.mid, wrn["id"], "ok", MEMBER, payload=b"bytes"),
            lambda: self.ext.record_integration_connector(
                self.mid, "INT-9", "SYS-1", MEMBER,
                endpoint="https://example.invalid"),
            lambda: self.ext.record_integration_connector(
                self.mid, "INT-9", "SYS-1", MEMBER, api_key="secret"),
            lambda: self.ext.record_integration_exchange(
                self.mid, con["id"], "ok", MEMBER, payload=b"bytes"),
        ]
        for attempt in attempts:
            with self.assertRaises(TypeError):
                attempt()
        # Nothing was recorded by any rejected attempt.
        self.assertEqual(
            len(self.ext.list_incident_reports(self.mid, actor=MEMBER)), 1)
        self.assertEqual(
            self.ext.list_detection_requests(self.mid, MEMBER), [])
        self.assertEqual(
            len(self.ext.list_mass_warnings(self.mid, MEMBER)), 1)
        self.assertEqual(
            len(self.ext.list_integration_connectors(self.mid, MEMBER)), 1)

    def test_no_score_shaped_key_anywhere(self):
        rep = self.make_report()
        ana = self.ext.record_pattern_analysis(
            self.mid, "ANA-1", MEMBER, incident_report_id=rep["id"])
        self.ext.record_analysis_finding(self.mid, ana["id"], "R-1",
                                         MEMBER, label="reported")
        share = self.ext.record_share_authorization(
            self.mid, "OSH-1", "incident_report", rep["id"], "ORG-B",
            "ORG-A", MEMBER)
        self.ext.record_authorization_event(self.mid, share["id"],
                                            "granted", MEMBER)
        wrn = self.ext.record_mass_warning(self.mid, "WRN-1", "network",
                                           MEMBER)
        self.ext.record_warning_delivery(self.mid, wrn["id"], "sent",
                                         MEMBER)
        records = []
        records += self.ext.list_incident_reports(self.mid, actor=MEMBER)
        records += self.ext.list_pattern_analyses(self.mid, actor=MEMBER)
        records += self.ext.list_analysis_findings(self.mid, actor=MEMBER)
        records += self.ext.list_share_authorizations(self.mid,
                                                      actor=MEMBER)
        records += self.ext.list_authorization_events(self.mid,
                                                      actor=MEMBER)
        records += self.ext.list_mass_warnings(self.mid, MEMBER)
        records += self.ext.list_warning_deliveries(self.mid, actor=MEMBER)
        records.append(self.ext.incident_report_view(self.mid, rep["id"],
                                                     MEMBER))
        records.append(self.ext.share_authorization_view(
            self.mid, share["id"], MEMBER))
        records.append(self.ext.mass_warning_view(self.mid, wrn["id"],
                                                  MEMBER))

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from walk(item)
            elif isinstance(value, list):
                for item in value:
                    yield from walk(item)

        forbidden = ("score", "rating", "rank", "threat_level",
                     "risk", "predict", "severity")
        for record in records:
            for key in walk(record):
                for token in forbidden:
                    self.assertNotIn(token, key)


class TestAccessAndBoundariesAddition(AdditionFixture):
    """High apparatus on the addition surface: the auditor role
    is denied every operation (read and write), the viewer
    cannot write, the matter membership boundary holds, a closed
    matter refuses new records, matters are isolated, and
    successful mutations land on the core hash-chained log under
    ext2_ action names."""

    def test_auditor_denied_write_read_and_view(self):
        rep = self.make_report()
        with self.assertRaises(PermissionDenied):
            self.ext.file_incident_report(self.mid, "RPT-9", "web",
                                          AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.get_incident_report(self.mid, rep["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.incident_report_view(self.mid, rep["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.record_mass_warning(self.mid, "WRN-9", "network",
                                         AUDITOR)
        self.assertIn("ext2_incident_report_file:denied",
                      self.audit_actions())
        self.assertIn("ext2_mass_warning_record:denied",
                      self.audit_actions())

    def test_viewer_cannot_write_but_can_read(self):
        with self.assertRaises(PermissionDenied):
            self.ext.file_incident_report(self.mid, "RPT-1", "web", VIEWER)
        rep = self.make_report()
        got = self.ext.get_incident_report(self.mid, rep["id"], VIEWER)
        self.assertEqual(got["id"], rep["id"])

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.file_incident_report(self.mid, "RPT-1", "web",
                                          OUTSIDER)
        rep = self.make_report()
        with self.assertRaises(PermissionDenied):
            self.ext.get_incident_report(self.mid, rep["id"], OUTSIDER)
        self.assertIn("ext2_incident_report_file:denied",
                      self.audit_actions())

    def test_closed_matter_rejects_writes(self):
        self.store.close_matter(self.mid, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.file_incident_report(self.mid, "RPT-1", "web", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_mass_warning(self.mid, "WRN-1", "network",
                                         MEMBER)

    def test_cross_matter_isolation(self):
        rep = self.make_report()
        other = self.store.create_matter("MATTER-REF-002", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_incident_report(other["id"], rep["id"], MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_pattern_analysis(
                other["id"], "ANA-1", MEMBER,
                incident_report_id=rep["id"])
        self.assertEqual(
            self.ext.list_incident_reports(other["id"], actor=MEMBER), [])

    def test_admin_can_write(self):
        rep = self.ext.file_incident_report(self.mid, "RPT-1", "web",
                                            ADMIN)
        self.assertEqual(rep["created_by"], "alice")

    def test_mutations_audited_under_ext2_names(self):
        self.make_report()
        self.ext.record_mass_warning(self.mid, "WRN-1", "network", MEMBER)
        actions = self.audit_actions()
        self.assertIn("ext2_incident_report_file", actions)
        self.assertIn("ext2_mass_warning_record", actions)
        self.assertEqual(self.audit.verify_chain(), (True, None))


class TestAuthorizationNegativeControl(AdditionFixture):
    """Fresh negative control: an authorization's current state
    is the label on the LATEST recorded authorization event."""

    def _canonical_case(self, ext):
        rep = ext.file_incident_report(self.mid, "RPT-1", "web", MEMBER,
                                       report_sha256=REPORT_SHA256)
        share = ext.record_share_authorization(
            self.mid, "OSH-1", "incident_report", rep["id"], "ORG-B",
            "ORG-A", MEMBER)
        ext.record_authorization_event(self.mid, share["id"],
                                       "granted by originator", MEMBER)
        ext.record_authorization_event(self.mid, share["id"],
                                       "revoked by originator", MEMBER)
        return ext.share_authorization_view(self.mid, share["id"], MEMBER)

    def test_canonical_current_label_is_latest(self):
        view = self._canonical_case(self.ext)
        self.assertEqual(view["current_authorization_label"],
                         "revoked by originator")
        self.assertEqual(view["authorization_event_count"], 2)

    def test_mutant_first_event_outcome_differs(self):
        mutant = MutantExtensionsAddition(self.store)
        view = self._canonical_case(mutant)
        self.assertEqual(view["current_authorization_label"],
                         "granted by originator")

    def test_mutant_outcome_rejected_as_canonical(self):
        mutant = MutantExtensionsAddition(self.store)
        view = self._canonical_case(mutant)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_authorization_label"],
                             "revoked by originator")

    def test_no_events_reads_recorded_initial_state(self):
        # Orientation-symmetric: with no events, both the real
        # seam and the mutant read the recorded initial state.
        for ext in (self.ext, MutantExtensionsAddition(self.store)):
            rep = ext.file_incident_report(
                self.mid, "RPT-1", "web", MEMBER,
                report_sha256=REPORT_SHA256)
            share = ext.record_share_authorization(
                self.mid, "OSH-1", "incident_report", rep["id"], "ORG-B",
                "ORG-A", MEMBER)
            view = ext.share_authorization_view(self.mid, share["id"],
                                                MEMBER)
            self.assertEqual(view["current_authorization_label"],
                             "authorized_as_recorded")


class TestFailClosedAddition(unittest.TestCase):
    """AU-5 on the addition surface: extension mutations audit
    BEFORE commit, so a failed audit write commits nothing and
    consumes no id, and the hash chain still verifies."""

    def _broken_path(self, good_path):
        # A path under an existing *file*: opening it raises
        # NotADirectoryError, an OSError -- the write cannot succeed.
        return os.path.join(good_path, "child.jsonl")

    def test_addition_create_rolls_back_on_audit_failure(self):
        path = _scratch_file("audit-ext2-failclosed-test.jsonl")
        audit = AuditLog(path=path)
        store, audit, matter = make_store(audit=audit)
        ext = LawEnfExtensionsAddition(store)
        audit.path = self._broken_path(path)
        with self.assertRaises(AuditWriteError):
            ext.file_incident_report(matter["id"], "RPT-1", "web", MEMBER,
                                     report_sha256=REPORT_SHA256)
        audit.path = path
        # Nothing was committed and no id was consumed.
        self.assertEqual(
            ext.list_incident_reports(matter["id"], actor=MEMBER), [])
        rep = ext.file_incident_report(matter["id"], "RPT-1", "web",
                                       MEMBER,
                                       report_sha256=REPORT_SHA256)
        self.assertEqual(rep["id"], "inc-1")
        self.assertEqual(audit.verify_chain(), (True, None))
