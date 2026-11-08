"""Final GAPS batch, second unit -- remainder addition tests.

Pins the addition surface in ``custsvc/extensions_addition.py``
for the 2 open entries of the "Remainder Addition -- Customer
Service L3-adjacent (+1 fork)" GAPS.md section (see
``../BATCH-ADDITION.md``):

- the survey entry (built, records form): instrument definitions
  with their scale held as recorded terms, response records
  holding each reported value verbatim, feedback-signal records
  over opaque references; no figure is aggregated anywhere (views
  derive record counts and the latest record only), and recording
  responses/signals creates no core case and no core alert;
- the connector entry (reference): every record carries
  ``reference_stub: True`` and ``reference_transport: True`` with
  its not-here flags, and exchange outcomes are stored verbatim;
- RBAC rides the core matrix: the auditor role is denied every
  operation, denials are audited, mutations land on the core's
  hash-chained log and it still verifies, and a failed audit write
  rolls the record and its id back (AU-5);
- the privacy discipline: respondents are registered core
  requesters by opaque ref, content-shaped arguments raise
  ``TypeError``, and a recursive scan over every record and view
  finds no content- or score-shaped key and no float;
- the fresh negative control: the latest-record seam is
  load-bearing (three-leg test -- canonical, mutant,
  mutant-as-expectation). The live drill is recorded in
  tests/README.md.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from custsvc.errors import (  # noqa: E402
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from custsvc.extensions_addition import CustsvcExtensionsAddition  # noqa: E402

from custsvc_helpers import ADMIN, AGENT, AUDITOR, VIEWER, make_case, make_store  # noqa: E402


def make_exta(audit=None):
    store, audit, requester, rsp1, rsp2 = make_store(audit=audit)
    return CustsvcExtensionsAddition(store), store, audit, requester


def make_survey(ext, actor=ADMIN):
    return ext.create_survey_instrument(
        "Citizen experience survey", ["survey", "digital", "call"],
        1, 5, actor)


class TestSurveyInstruments(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()

    def test_instrument_shape_has_no_tally(self):
        survey = make_survey(self.ext)
        self.assertEqual(
            set(survey),
            {"id", "name", "channels", "scale_low", "scale_high",
             "collected_here", "created_by", "created_utc"})
        self.assertEqual(survey["id"], "survey-1")
        self.assertIs(survey["collected_here"], False)
        self.assertEqual(self.ext.get_survey_instrument("survey-1", VIEWER),
                         survey)
        self.assertEqual(self.ext.list_survey_instruments(VIEWER), [survey])

    def test_instrument_validation_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument("X", ["survey"], 5, 5, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument("X", ["survey"], True, 5, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument("X", ["survey"], 1, 5.0, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument("X", ["smoke_signal"], 1, 5,
                                              ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument("X", [], 1, 5, ADMIN)
        survey = make_survey(self.ext)
        self.assertEqual(survey["id"], "survey-1")

    def test_channels_deduplicated_in_order(self):
        survey = self.ext.create_survey_instrument(
            "X", ["digital", "survey", "digital"], 0, 10, ADMIN)
        self.assertEqual(survey["channels"], ["digital", "survey"])


class TestSurveyResponses(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()
        make_survey(self.ext)

    def test_response_stores_reported_value_verbatim(self):
        response = self.ext.record_survey_response(
            "survey-1", "citizen-001", "survey", 4, AGENT)
        self.assertEqual(
            set(response),
            {"id", "survey_id", "requester_ref", "channel",
             "reported_value", "reported", "collected_here",
             "created_by", "created_utc"})
        self.assertEqual(response["id"], "sresp-1")
        self.assertEqual(response["reported_value"], 4)
        self.assertIs(response["reported"], True)
        self.assertEqual(self.ext.list_survey_responses("survey-1", VIEWER),
                         [response])

    def test_response_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_survey_response("survey-9", "citizen-001",
                                            "survey", 3, ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_survey_response("survey-1", "ghost-9",
                                            "survey", 3, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response("survey-1", "citizen-001",
                                            "video", 3, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response("survey-1", "citizen-001",
                                            "survey", 6, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response("survey-1", "citizen-001",
                                            "survey", 0, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response("survey-1", "citizen-001",
                                            "survey", 4.5, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response("survey-1", "citizen-001",
                                            "survey", True, ADMIN)
        self.assertEqual(self.ext.list_survey_responses("survey-1", ADMIN),
                         [])

    def test_view_counts_and_latest_without_aggregation(self):
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "survey", 2, AGENT)
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "digital", 5, AGENT)
        view = self.ext.survey_view("survey-1", ADMIN)
        self.assertEqual(view["response_count"], 2)
        self.assertEqual(view["responses_by_channel"],
                         {"survey": 1, "digital": 1})
        self.assertEqual(view["latest_response_id"], "sresp-2")
        self.assertEqual(view["latest_reported_value"], 5)
        self.assertIs(view["derived"], True)
        # No aggregate over reported values exists on the view.
        for key in view:
            for part in ("mean", "average", "total", "sum", "tally",
                         "distribution", "rank"):
                self.assertNotIn(part, key.lower())
        # The stored instrument still carries no derived key.
        stored = self.ext.get_survey_instrument("survey-1", ADMIN)
        self.assertNotIn("response_count", stored)
        self.assertNotIn("latest_reported_value", stored)

    def test_empty_view(self):
        view = self.ext.survey_view("survey-1", ADMIN)
        self.assertEqual(view["response_count"], 0)
        self.assertIsNone(view["latest_response_id"])
        self.assertIsNone(view["latest_reported_value"])


class TestFeedbackSignals(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()
        make_survey(self.ext)
        self.case = make_case(self.store, self.requester)

    def test_signal_shape_and_bindings(self):
        alert = self.store.ingest_alert("survey-feed", "Signal spike",
                                        "warning", AGENT,
                                        case_id=self.case["id"])
        signal = self.ext.record_feedback_signal(
            "signal-001", "iot", AGENT, survey_id="survey-1",
            requester_ref="citizen-001", case_id=self.case["id"],
            alert_id=alert["id"])
        self.assertEqual(
            set(signal),
            {"id", "signal_ref", "channel", "survey_id", "requester_ref",
             "case_id", "alert_id", "reported", "collected_here",
             "created_by", "created_utc"})
        self.assertEqual(signal["id"], "fsig-1")
        self.assertIs(signal["collected_here"], False)
        self.assertEqual(
            self.ext.list_feedback_signals(ADMIN, channel="iot"), [signal])
        self.assertEqual(
            self.ext.list_feedback_signals(ADMIN, channel="call"), [])

    def test_signal_bindings_must_exist(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_feedback_signal("s-1", "survey", ADMIN,
                                            survey_id="survey-9")
        with self.assertRaises(NotFoundError):
            self.ext.record_feedback_signal("s-1", "survey", ADMIN,
                                            requester_ref="ghost-9")
        with self.assertRaises(NotFoundError):
            self.ext.record_feedback_signal("s-1", "survey", ADMIN,
                                            case_id="case-9")
        with self.assertRaises(NotFoundError):
            self.ext.record_feedback_signal("s-1", "survey", ADMIN,
                                            alert_id="alert-9")
        with self.assertRaises(ValidationError):
            self.ext.record_feedback_signal("s-1", "smoke_signal", ADMIN)
        self.assertEqual(self.ext.list_feedback_signals(ADMIN), [])

    def test_signals_and_responses_create_no_core_records(self):
        cases_before = self.store.list_cases(ADMIN)
        alerts_before = self.store.list_alerts(ADMIN)
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "survey", 1, AGENT)
        self.ext.record_feedback_signal("signal-001", "digital", AGENT,
                                        survey_id="survey-1",
                                        case_id=self.case["id"])
        self.assertEqual(self.store.list_cases(ADMIN), cases_before)
        self.assertEqual(self.store.list_alerts(ADMIN), alerts_before)

    def test_summary_counts_only(self):
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "survey", 3, AGENT)
        self.ext.record_feedback_signal("signal-001", "digital", AGENT,
                                        survey_id="survey-1")
        self.ext.record_feedback_signal("signal-002", "digital", AGENT)
        summary = self.ext.feedback_summary(ADMIN)
        self.assertEqual(summary["instruments"], 1)
        self.assertEqual(summary["responses"], 1)
        self.assertEqual(summary["signals"], 2)
        self.assertEqual(summary["responses_by_channel"], {"survey": 1})
        self.assertEqual(summary["signals_by_channel"], {"digital": 2})
        self.assertIs(summary["collected_here"], False)


class TestConnectors(unittest.TestCase):
    """Entry: platform connectors & integration API (reference)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()

    def test_connector_shape_and_labels(self):
        conn = self.ext.register_connector("conn-crm-1", "platform_connector",
                                           "CRM platform", ADMIN)
        self.assertEqual(
            set(conn),
            {"id", "connector_ref", "kind", "platform_label",
             "reference_stub", "reference_transport", "connected_here",
             "synced_here", "state", "created_by", "created_utc"})
        self.assertEqual(conn["id"], "conn-1")
        self.assertIs(conn["reference_stub"], True)
        self.assertIs(conn["reference_transport"], True)
        self.assertIs(conn["connected_here"], False)
        self.assertIs(conn["synced_here"], False)
        self.assertEqual(self.ext.list_connectors(VIEWER), [conn])

    def test_connector_ref_unique_and_kind_validated(self):
        self.ext.register_connector("conn-crm-1", "api_surface", "P", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.register_connector("conn-crm-1", "api_surface", "P",
                                        ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.register_connector("conn-2", "webhook", "P", ADMIN)
        self.assertEqual(len(self.ext.list_connectors(ADMIN)), 1)

    def test_exchange_flow_and_view(self):
        self.ext.register_connector("conn-crm-1", "platform_connector",
                                    "CRM platform", ADMIN)
        first = self.ext.record_exchange("conn-1", "inbound",
                                         "reported_partial", AGENT,
                                         records_reported=12)
        self.assertEqual(first["id"], "exch-1")
        self.assertEqual(first["records_reported"], 12)
        self.assertIs(first["imported_here"], False)
        self.assertIs(first["executed_here"], False)
        self.assertIs(first["reference_transport"], True)
        self.ext.record_exchange("conn-1", "outbound", "reported_completed",
                                 AGENT)
        view = self.ext.connector_view("conn-1", ADMIN)
        self.assertEqual(view["exchange_count"], 2)
        self.assertEqual(view["latest_exchange_outcome"],
                         "reported_completed")
        self.assertNotIn("exchange_count",
                         self.ext.get_connector("conn-1", ADMIN))

    def test_exchange_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_exchange("conn-9", "inbound",
                                     "reported_completed", ADMIN)
        self.ext.register_connector("conn-crm-1", "api_surface", "P", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange("conn-1", "sideways",
                                     "reported_completed", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange("conn-1", "inbound", "synced", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange("conn-1", "inbound",
                                     "reported_completed", ADMIN,
                                     records_reported=-1)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange("conn-1", "inbound",
                                     "reported_completed", ADMIN,
                                     records_reported=1.5)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange("conn-1", "inbound",
                                     "reported_completed", ADMIN,
                                     records_reported=True)
        with self.assertRaises(NotFoundError):
            self.ext.record_exchange("conn-1", "inbound",
                                     "reported_completed", ADMIN,
                                     case_id="case-9")
        self.assertEqual(self.ext.list_exchanges("conn-1", ADMIN), [])


class TestAccessAndAudit(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()

    def test_auditor_denied_every_operation_but_core_audit_works(self):
        make_survey(self.ext)
        self.ext.register_connector("conn-1", "api_surface", "P", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.create_survey_instrument("X", ["survey"], 1, 5, AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_survey_instruments(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.survey_view("survey-1", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.feedback_summary(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_connectors(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.record_exchange("conn-1", "inbound",
                                     "reported_completed", AUDITOR)
        # The auditor's core duty is untouched by the denial.
        self.assertEqual(self.audit.verify_chain(), (True, None))
        self.assertTrue(self.audit.query(actor="dana"))

    def test_denied_attempt_is_audited_with_suffix(self):
        with self.assertRaises(PermissionDenied):
            make_survey(self.ext, actor=VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "exta_survey_instrument_create:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")
        self.assertEqual(self.ext.list_survey_instruments(ADMIN), [])

    def test_mutations_land_on_chain_and_it_verifies(self):
        make_survey(self.ext)
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "survey", 4, AGENT)
        self.ext.register_connector("conn-1", "api_surface", "P", ADMIN)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("exta_survey_instrument_create", actions)
        self.assertIn("exta_survey_response", actions)
        self.assertIn("exta_connector_register", actions)
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_audit_failure_rolls_back_record_and_id(self):
        original = self.audit.record

        def broken(*args, **kwargs):
            raise AuditWriteError("audit store unavailable")

        self.audit.record = broken
        try:
            with self.assertRaises(AuditWriteError):
                make_survey(self.ext)
            with self.assertRaises(AuditWriteError):
                self.ext.register_connector("conn-1", "api_surface", "P",
                                            ADMIN)
        finally:
            self.audit.record = original
        self.assertEqual(self.ext.list_survey_instruments(ADMIN), [])
        self.assertEqual(self.ext.list_connectors(ADMIN), [])
        survey = make_survey(self.ext)
        conn = self.ext.register_connector("conn-1", "api_surface", "P",
                                           ADMIN)
        self.assertEqual(survey["id"], "survey-1")
        self.assertEqual(conn["id"], "conn-1")
        self.assertEqual(self.audit.verify_chain(), (True, None))


_FORBIDDEN_KEY_PARTS = (
    "score", "sentiment", "intent", "csat",
    "transcript", "message", "content", "comment", "mean", "average",
)


def _walk(value, path="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _walk(item, path + "." + str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, "%s[%d]" % (path, index))


class TestPrivacyAndScoreScans(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_exta()

    def test_content_shaped_arguments_raise_type_error(self):
        make_survey(self.ext)
        with self.assertRaises(TypeError):
            self.ext.record_survey_response(
                "survey-1", "citizen-001", "survey", 4, ADMIN,
                comment="great")
        with self.assertRaises(TypeError):
            self.ext.record_feedback_signal(
                "s-1", "survey", ADMIN, transcript="hello")
        with self.assertRaises(TypeError):
            self.ext.register_connector(
                "conn-1", "api_surface", "P", ADMIN, body="payload")
        with self.assertRaises(TypeError):
            self.ext.create_survey_instrument(
                "X", ["survey"], 1, 5, ADMIN, score=5)
        with self.assertRaises(TypeError):
            self.ext.record_exchange(
                "conn-1", "inbound", "reported_completed", ADMIN,
                message_text="hi")

    def test_no_content_or_score_key_and_no_float_anywhere(self):
        make_survey(self.ext)
        self.ext.record_survey_response("survey-1", "citizen-001",
                                        "survey", 4, ADMIN)
        self.ext.record_feedback_signal("s-1", "digital", ADMIN,
                                        survey_id="survey-1")
        self.ext.register_connector("conn-1", "api_surface", "P", ADMIN)
        self.ext.record_exchange("conn-1", "inbound", "reported_completed",
                                 ADMIN, records_reported=3)
        surface = []
        surface += self.ext.list_survey_instruments(ADMIN)
        surface += self.ext.list_survey_responses("survey-1", ADMIN)
        surface += self.ext.list_feedback_signals(ADMIN)
        surface += [self.ext.survey_view("survey-1", ADMIN)]
        surface += [self.ext.feedback_summary(ADMIN)]
        surface += self.ext.list_connectors(ADMIN)
        surface += self.ext.list_exchanges("conn-1", ADMIN)
        surface += [self.ext.connector_view("conn-1", ADMIN)]
        self.assertTrue(surface)
        for record in surface:
            for path, key in _walk(record):
                for part in _FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, str(key).lower(),
                        "%s key %r contains %r" % (path, key, part))
            self._assert_no_floats(record)

    def _assert_no_floats(self, value):
        if isinstance(value, dict):
            for item in value.values():
                self._assert_no_floats(item)
        elif isinstance(value, list):
            for item in value:
                self._assert_no_floats(item)
        else:
            self.assertNotIsInstance(value, float)


class FirstRecordAddition(CustsvcExtensionsAddition):
    """Mutant: latest-record derivations read the FIRST record
    instead of the latest -- the in-suite form of this unit's
    fresh negative control."""

    def _latest_record(self, records):
        if not records:
            return None
        return records[0]


class TestLatestRecordNegativeControl(unittest.TestCase):
    """Three-leg control: the latest-record seam must be
    load-bearing for both views that derive through it."""

    def _walk(self, ext):
        make_survey(ext)
        ext.record_survey_response("survey-1", "citizen-001", "survey", 2,
                                   ADMIN)
        ext.record_survey_response("survey-1", "citizen-001", "digital", 5,
                                   ADMIN)
        ext.register_connector("conn-x", "api_surface", "P", ADMIN)
        ext.record_exchange("conn-1", "inbound", "reported_partial", ADMIN)
        ext.record_exchange("conn-1", "outbound", "reported_completed",
                            ADMIN)

    def test_canonical_derives_from_latest_record(self):
        ext, store, audit, requester = make_exta()
        self._walk(ext)
        self.assertEqual(ext.survey_view("survey-1", ADMIN)
                         ["latest_reported_value"], 5)
        self.assertEqual(ext.connector_view("conn-1", ADMIN)
                         ["latest_exchange_outcome"], "reported_completed")

    def test_mutant_derives_from_first_record(self):
        store, audit, requester, _, _ = make_store()
        ext = FirstRecordAddition(store)
        self._walk(ext)
        self.assertEqual(ext.survey_view("survey-1", ADMIN)
                         ["latest_reported_value"], 2)
        self.assertEqual(ext.connector_view("conn-1", ADMIN)
                         ["latest_exchange_outcome"], "reported_partial")

    def test_mutant_as_expectation_fails(self):
        store, audit, requester, _, _ = make_store()
        ext = FirstRecordAddition(store)
        self._walk(ext)
        with self.assertRaises(AssertionError):
            self.assertEqual(ext.survey_view("survey-1", ADMIN)
                             ["latest_reported_value"], 5)
        with self.assertRaises(AssertionError):
            self.assertEqual(ext.connector_view("conn-1", ADMIN)
                             ["latest_exchange_outcome"],
                             "reported_completed")


if __name__ == "__main__":
    unittest.main()
