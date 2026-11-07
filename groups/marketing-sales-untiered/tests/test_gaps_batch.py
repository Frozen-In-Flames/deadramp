"""Final GAPS batch — Untiered Set 18 extension surface.

Pins, per GAPS.md entry (idx in gaps-batch/inventory.json):

- idx 912 AI models / agents — reference records (request,
  reported outcome, reported evaluation, agent definitions as
  data), stub-labeled, with result content refused by signature.
- idx 913 Live discovery feeds & contract-search engines —
  reference records (feed definitions as data, the feed's own
  reported counts), transport-labeled; a report registers no
  core opportunity.
- idx 914 Market intelligence & competitor / forecast analytics
  — built: analyst-recorded intelligence and forecast reports,
  and a market view of deterministic counts derived at read over
  the substrate's own records, method stated, counts only.
- idx 915 Proposal generation engine — reference records
  (re-judged; see BATCH.md): requests and reported outcomes, no
  parameter can carry drafted text, a reported result names an
  existing core content-version record.
- idx 916 Workflow execution engine — reference records:
  execution requests and reported outcomes that leave the core
  workflow record deep-equal.
- idx 917 Segmentation engine — reference records (re-judged):
  computation requests with criteria as data and the engine's
  reported counts; the core segment record is untouched.
- idx 918 Email sending transport & deliverability — reference
  records (re-judged): send requests and transport receipts that
  create no core delivery and move no campaign status.
- idx 919 Bounce/complaint handling automation, campaign
  template management, preference management — built: rule
  definitions as data, a handling queue derived at read from
  core records, handling-decision records that create no core
  suppression, template metadata in the core content form, and
  preference records whose current value derives at read.

Plus the cross-cutting pins: tier null on the whole surface (a
recursive scan finds no tier / baseline / equivalence key, and
none of the core's forbidden key parts either), RBAC through the
core matrix, extension mutations on the core audit log, and
rollback when an audit write fails.
"""

import copy
import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, CONTACT_B, OCCURRED,
                                 OPERATOR, VIEWER, make_campaign,
                                 make_opportunity, make_org, make_store)

import marketsales.extensions as extensions_module

from marketsales.audit import AuditLog
from marketsales.errors import (NotFoundError, PermissionDenied,
                                ValidationError)
from marketsales.extensions import MarketSalesExtensions


def make_ext():
    store, audit = make_store()
    return store, audit, MarketSalesExtensions(store)


TIER_KEY_PARTS = ("tier", "baseline", "cmmc", "fedramp",
                  "impact_level", "equivalen")
FORBIDDEN_KEY_PARTS = ("score", "grade", "rank", "rate", "email",
                       "body", "content_text", "text_body", "ssn",
                       "password", "secret")


def scan_keys(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            for part in TIER_KEY_PARTS + FORBIDDEN_KEY_PARTS:
                if part in key.lower():
                    raise AssertionError(
                        "forbidden key part %r at %s.%s"
                        % (part, path, key))
            scan_keys(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            scan_keys(value, "%s[%d]" % (path, index))


class AiSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)

    def test_request_record_is_a_labeled_reference_record(self):
        record = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft support",
            opportunity_id=self.opp["id"])
        self.assertEqual(record["id"], "aireq-1")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["inference_here"], False)
        self.assertEqual(record["opportunity_id"], self.opp["id"])
        self.assertIsNone(record["campaign_id"])

    def test_report_refuses_result_content_by_signature(self):
        request = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft support")
        with self.assertRaises(TypeError):
            self.ext.record_ai_report(
                OPERATOR, request["id"], "completed",
                content="the drafted text")
        with self.assertRaises(TypeError):
            self.ext.record_ai_report(
                OPERATOR, request["id"], "completed",
                result_text="the drafted text")
        with self.assertRaises(TypeError):
            self.ext.register_ai_request(
                OPERATOR, self.org["id"], "MODEL-REF-1", "draft",
                result="the drafted text")

    def test_report_stores_outcome_verbatim_and_holds_no_result(self):
        request = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft support")
        report = self.ext.record_ai_report(
            OPERATOR, request["id"], "completed",
            result_ref="RESULT-REF-1")
        self.assertEqual(report["outcome_label"], "completed")
        self.assertEqual(report["result_ref"], "RESULT-REF-1")
        self.assertIs(report["result_held_here"], False)
        self.assertIs(report["reference_stub"], True)

    def test_evaluation_figure_stored_verbatim(self):
        request = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft support")
        by_int = self.ext.record_ai_evaluation(
            OPERATOR, request["id"], 87, figure_label="vendor bench")
        self.assertEqual(by_int["reported_figure"], 87)
        self.assertIs(by_int["computed_here"], False)
        by_label = self.ext.record_ai_evaluation(
            OPERATOR, request["id"], "pass", figure_label="review")
        self.assertEqual(by_label["reported_figure"], "pass")

    def test_evaluation_rejects_floats_and_bools(self):
        request = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft support")
        with self.assertRaises(ValidationError):
            self.ext.record_ai_evaluation(OPERATOR, request["id"], 0.87)
        with self.assertRaises(ValidationError):
            self.ext.record_ai_evaluation(OPERATOR, request["id"], True)

    def test_request_requires_existing_bindings_and_consumes_no_id(
            self):
        with self.assertRaises(NotFoundError):
            self.ext.register_ai_request(
                OPERATOR, self.org["id"], "MODEL-REF-1", "draft",
                opportunity_id="opp-999")
        with self.assertRaises(NotFoundError):
            self.ext.register_ai_request(
                OPERATOR, "org-999", "MODEL-REF-1", "draft")
        record = self.ext.register_ai_request(
            OPERATOR, self.org["id"], "MODEL-REF-1", "draft")
        self.assertEqual(record["id"], "aireq-1")

    def test_agent_definition_is_data_and_never_executes(self):
        definition = self.ext.register_agent_definition(
            OPERATOR, self.org["id"], "Pursuit agent",
            ["watch feeds", "summarize matches"])
        self.assertEqual(
            definition["steps"],
            [{"step": 1, "action_label": "watch feeds"},
             {"step": 2, "action_label": "summarize matches"}])
        self.assertIs(definition["executed_here"], False)
        self.assertIs(definition["reference_stub"], True)
        for name in ("execute", "run", "execute_agent", "run_agent"):
            self.assertFalse(hasattr(MarketSalesExtensions, name),
                             name)


class DiscoveryFeedTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)

    def test_feed_definition_labels(self):
        feed = self.ext.register_discovery_feed(
            OPERATOR, self.org["id"], "SAM feed", "sam.gov",
            query_label="IDIQ recompetes")
        self.assertIs(feed["reference_stub"], True)
        self.assertIs(feed["reference_transport"], True)
        self.assertIs(feed["fetched_here"], False)
        self.assertIs(feed["searched_here"], False)
        self.assertIs(feed["active"], True)

    def test_feed_toggle_records_state_only(self):
        feed = self.ext.register_discovery_feed(
            OPERATOR, self.org["id"], "SAM feed", "sam.gov")
        toggled = self.ext.set_discovery_feed_active(
            OPERATOR, feed["id"], False)
        self.assertIs(toggled["active"], False)
        self.assertEqual(self.store.list_opportunities(ADMIN), [])

    def test_report_counts_are_data_and_register_nothing(self):
        feed = self.ext.register_discovery_feed(
            OPERATOR, self.org["id"], "SAM feed", "sam.gov")
        report = self.ext.record_discovery_report(
            OPERATOR, feed["id"], 42, reported_new_count=3,
            period_label="2026-W02")
        self.assertEqual(report["reported_count"], 42)
        self.assertEqual(report["reported_new_count"], 3)
        self.assertIs(report["reference_transport"], True)
        # The report registers nothing: discovery enters the core
        # only through a human's own registration.
        self.assertEqual(self.store.list_opportunities(ADMIN), [])
        with self.assertRaises(ValidationError):
            self.ext.record_discovery_report(OPERATOR, feed["id"], 1.5)
        with self.assertRaises(ValidationError):
            self.ext.record_discovery_report(OPERATOR, feed["id"], True)


class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)

    def test_intelligence_report_record_shape(self):
        report = self.ext.record_intelligence_report(
            OPERATOR, self.org["id"], "IDIQ market",
            "incumbent recompete announced", "SRC-1",
            competitor_label="Rival Co")
        self.assertEqual(report["id"], "intel-1")
        self.assertEqual(report["competitor_label"], "Rival Co")
        self.assertEqual(report["source_ref"], "SRC-1")

    def test_forecast_is_a_citation_not_a_computation(self):
        forecast = self.ext.record_forecast(
            OPERATOR, self.org["id"], "FY27 widget IDIQ", "FY27", 5,
            "SRC-2", basis_label="agency forecast page")
        self.assertEqual(forecast["reported_count"], 5)
        self.assertIs(forecast["computed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_forecast(
                OPERATOR, self.org["id"], "bad", "FY27", -1, "SRC-3")

    def test_market_view_counts_the_substrates_own_records(self):
        other = self.store.create_organization(
            ADMIN, "ORG-0002", "Second office")
        other_opp = self.store.create_opportunity(
            OPERATOR, other["id"], "OPP-REF-0002",
            "Department of Samples", "Other title", "2026-01-06")
        self.store.record_evaluation(
            OPERATOR, self.opp["id"], "EV-1", "pursue")
        self.store.record_evaluation(
            OPERATOR, other_opp["id"], "EV-1", "watch")
        self.store.create_pipeline_entry(OPERATOR, self.opp["id"])
        self.ext.record_intelligence_report(
            OPERATOR, self.org["id"], "IDIQ market", "note", "SRC-1")
        view = self.ext.market_view(ADMIN)
        self.assertEqual(view["opportunities_total"], 2)
        self.assertEqual(
            view["opportunities_by_agency_label"],
            {"Department of Examples": 1,
             "Department of Samples": 1})
        self.assertEqual(view["evaluations_by_decision"],
                         {"pursue": 1, "watch": 1})
        self.assertEqual(view["pipeline_by_stage"],
                         {"identified": 1})
        self.assertEqual(view["intelligence_reports"], 1)
        # Derived at read: a new record moves the view.
        self.store.record_evaluation(
            OPERATOR, self.opp["id"], "EV-2", "pursue")
        self.assertEqual(
            self.ext.market_view(ADMIN)["evaluations_by_decision"],
            {"pursue": 2, "watch": 1})
        # The org filter narrows every count.
        narrowed = self.ext.market_view(ADMIN, org_id=self.org["id"])
        self.assertEqual(narrowed["opportunities_total"], 1)
        self.assertEqual(narrowed["evaluations_by_decision"],
                         {"pursue": 2})

    def test_market_view_states_its_method_and_holds_counts_only(self):
        view = self.ext.market_view(ADMIN)
        self.assertEqual(
            view["method"],
            "deterministic_counts_over_recorded_records")
        self.assertIs(view["counts_only"], True)
        scan_keys(view)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)

    def test_generation_request_refuses_text_by_signature(self):
        with self.assertRaises(TypeError):
            self.ext.request_proposal_generation(
                OPERATOR, self.opp["id"], "Volume I", "section",
                content="draft text")
        with self.assertRaises(TypeError):
            self.ext.request_proposal_generation(
                OPERATOR, self.opp["id"], "Volume I", "section",
                text="draft text")

    def test_generation_records_hold_no_draft(self):
        request = self.ext.request_proposal_generation(
            OPERATOR, self.opp["id"], "Volume I", "section")
        self.assertIs(request["drafted_here"], False)
        self.assertIs(request["reference_stub"], True)
        report = self.ext.record_generation_report(
            OPERATOR, request["id"], "no draft produced")
        self.assertIs(report["drafted_here"], False)
        self.assertIs(report["result_held_here"], False)
        self.assertIsNone(report["result_content_id"])

    def test_generation_report_binds_existing_content_version(self):
        request = self.ext.request_proposal_generation(
            OPERATOR, self.opp["id"], "Volume I", "section")
        version = self.store.create_content_version(
            OPERATOR, self.opp["id"], "Volume I", "section", 1, 128)
        before = copy.deepcopy(
            self.store.list_content(ADMIN,
                                    opportunity_id=self.opp["id"]))
        report = self.ext.record_generation_report(
            OPERATOR, request["id"], "draft produced",
            result_content_id=version["id"])
        self.assertEqual(report["result_content_id"], version["id"])
        self.assertEqual(
            self.store.list_content(ADMIN,
                                    opportunity_id=self.opp["id"]),
            before)
        with self.assertRaises(NotFoundError):
            self.ext.record_generation_report(
                OPERATOR, request["id"], "draft produced",
                result_content_id="pro-999")
        other_opp = self.store.create_opportunity(
            OPERATOR, self.org["id"], "OPP-REF-0002",
            "Department of Examples", "Second title", "2026-01-07")
        foreign = self.store.create_content_version(
            OPERATOR, other_opp["id"], "Volume I", "section", 1, 64)
        with self.assertRaises(NotFoundError):
            self.ext.record_generation_report(
                OPERATOR, request["id"], "draft produced",
                result_content_id=foreign["id"])


class WorkflowExecutionTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.workflow = self.store.create_workflow(
            OPERATOR, self.org["id"], "Digest",
            "new opportunity posted")

    def test_execution_request_leaves_the_core_workflow_unchanged(
            self):
        before = copy.deepcopy(self.store.list_workflows(ADMIN))
        request = self.ext.request_workflow_execution(
            OPERATOR, self.workflow["id"], {"window_days": 7})
        self.assertEqual(request["state"], "recorded_request_only")
        self.assertIs(request["executed_here"], False)
        self.assertIs(request["reference_stub"], True)
        self.ext.record_workflow_execution_report(
            OPERATOR, request["id"], "ran externally")
        self.assertEqual(self.store.list_workflows(ADMIN), before)

    def test_execution_parameters_are_validated_data(self):
        with self.assertRaises(ValidationError):
            self.ext.request_workflow_execution(
                OPERATOR, self.workflow["id"], {"window": 1.5})
        with self.assertRaises(ValidationError):
            self.ext.request_workflow_execution(
                OPERATOR, self.workflow["id"], {"score": 3})
        request = self.ext.request_workflow_execution(
            OPERATOR, self.workflow["id"],
            {"window_days": 7, "labels": ["a", "b"]})
        self.assertEqual(request["parameters"],
                         {"window_days": 7, "labels": ["a", "b"]})

    def test_execution_report_for_unknown_request(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_workflow_execution_report(
                OPERATOR, "wexec-999", "ran externally")
        with self.assertRaises(NotFoundError):
            self.ext.request_workflow_execution(OPERATOR, "wfl-999")


class SegmentationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        _campaign, _lst, self.segment = make_campaign(
            self.store, self.org)

    def test_segmentation_request_leaves_the_core_segment_unchanged(
            self):
        before = copy.deepcopy(self.store.list_segments(ADMIN))
        request = self.ext.request_segmentation(
            OPERATOR, self.segment["id"],
            [{"field": "role", "value": "pm"}])
        self.assertEqual(request["state"], "recorded_request_only")
        self.assertIs(request["computed_here"], False)
        self.assertIs(request["reference_stub"], True)
        self.assertEqual(self.store.list_segments(ADMIN), before)

    def test_segmentation_criteria_are_validated_data(self):
        with self.assertRaises(ValidationError):
            self.ext.request_segmentation(
                OPERATOR, self.segment["id"], [{"weight": 0.5}])
        with self.assertRaises(ValidationError):
            self.ext.request_segmentation(
                OPERATOR, self.segment["id"], "role = pm")
        with self.assertRaises(NotFoundError):
            self.ext.request_segmentation(
                OPERATOR, "seg-999", [{"field": "role"}])

    def test_segmentation_report_stores_the_engines_count_as_data(
            self):
        request = self.ext.request_segmentation(
            OPERATOR, self.segment["id"],
            [{"field": "role", "value": "pm"}])
        report = self.ext.record_segmentation_report(
            OPERATOR, request["id"], 288)
        self.assertEqual(report["reported_member_count"], 288)
        self.assertIs(report["computed_here"], False)
        # The core segment still carries its own recorded count.
        segment = self.store.list_segments(ADMIN)[0]
        self.assertEqual(segment["member_count"], 300)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.campaign, self.lst, _seg = make_campaign(
            self.store, self.org)

    def test_send_request_is_a_labeled_reference_record(self):
        request = self.ext.request_send(OPERATOR,
                                        self.campaign["id"])
        self.assertIs(request["sent_here"], False)
        self.assertIs(request["transmitted_here"], False)
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["reference_transport"], True)
        self.assertEqual(request["state"], "recorded_request_only")

    def test_receipt_creates_no_core_delivery_and_moves_no_status(
            self):
        status_before = self.store.get_campaign(
            ADMIN, self.campaign["id"])["status"]
        request = self.ext.request_send(OPERATOR,
                                        self.campaign["id"])
        receipt = self.ext.record_transport_receipt(
            OPERATOR, request["id"], 900, 12, 3,
            period_label="2026-01-10 send")
        self.assertEqual(receipt["reported_delivered"], 900)
        self.assertEqual(receipt["reported_bounced"], 12)
        self.assertIs(receipt["transmitted_here"], False)
        self.assertEqual(self.store.list_deliveries(ADMIN), [])
        self.assertEqual(self.store.list_engagements(ADMIN), [])
        self.assertEqual(
            self.store.get_campaign(ADMIN,
                                    self.campaign["id"])["status"],
            status_before)

    def test_receipt_counts_are_validated(self):
        request = self.ext.request_send(OPERATOR,
                                        self.campaign["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_transport_receipt(
                OPERATOR, request["id"], -1, 0, 0)
        with self.assertRaises(ValidationError):
            self.ext.record_transport_receipt(
                OPERATOR, request["id"], True, 0, 0)
        with self.assertRaises(NotFoundError):
            self.ext.record_transport_receipt(
                OPERATOR, "send-999", 1, 0, 0)


class HandlingTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.campaign, self.lst, _seg = make_campaign(
            self.store, self.org)

    def _bounce(self, contact=CONTACT_A):
        return self.store.record_delivery(
            OPERATOR, self.campaign["id"], contact, "bounced",
            OCCURRED)

    def test_rule_definition_is_data(self):
        rule = self.ext.register_handling_rule(
            OPERATOR, self.org["id"], "bounced_outcome",
            "record_suppression")
        self.assertIs(rule["applied_here"], False)
        self.assertIs(rule["active"], True)
        toggled = self.ext.set_handling_rule_active(
            OPERATOR, rule["id"], False)
        self.assertIs(toggled["active"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_handling_rule(
                OPERATOR, self.org["id"], "opened", "note_only")
        with self.assertRaises(ValidationError):
            self.ext.register_handling_rule(
                OPERATOR, self.org["id"], "bounced_outcome",
                "delete_contact")

    def test_bounced_delivery_enters_the_queue(self):
        self._bounce()
        pending = self.ext.pending_handling(ADMIN)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["contact_ref"], CONTACT_A)
        self.assertEqual(pending[0]["trigger"], "bounced_outcome")
        self.assertEqual(pending[0]["campaign_id"],
                         self.campaign["id"])

    def test_complaint_suppression_enters_the_queue(self):
        self.store.record_suppression(
            OPERATOR, self.lst["id"], CONTACT_B, "complaint")
        pending = self.ext.pending_handling(ADMIN)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["trigger"],
                         "complaint_suppression")
        self.assertIsNone(pending[0]["campaign_id"])

    def test_handling_record_drains_only_its_own_item(self):
        self._bounce(CONTACT_A)
        self._bounce(CONTACT_B)
        self.assertEqual(len(self.ext.pending_handling(ADMIN)), 2)
        self.ext.record_handling(
            OPERATOR, self.lst["id"], CONTACT_A, "bounced_outcome",
            "suppression_recorded", campaign_id=self.campaign["id"])
        pending = self.ext.pending_handling(ADMIN)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["contact_ref"], CONTACT_B)

    def test_handling_record_creates_no_core_suppression(self):
        self._bounce()
        before = copy.deepcopy(self.store.list_suppressions(ADMIN))
        self.ext.record_handling(
            OPERATOR, self.lst["id"], CONTACT_A, "bounced_outcome",
            "suppression_recorded", campaign_id=self.campaign["id"])
        self.assertEqual(self.store.list_suppressions(ADMIN), before)

    def test_handling_validates_campaign_list_match(self):
        other_campaign, other_list, _s = make_campaign(
            self.store, self.org)
        with self.assertRaises(ValidationError):
            self.ext.record_handling(
                OPERATOR, self.lst["id"], CONTACT_A,
                "bounced_outcome", "reviewed_no_action",
                campaign_id=other_campaign["id"])
        self.assertEqual(other_list["id"] != self.lst["id"], True)


class TemplateAndPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext = make_ext()
        self.org = make_org(self.store)
        self.campaign, self.lst, _seg = make_campaign(
            self.store, self.org)

    def test_template_is_metadata_only(self):
        template = self.ext.register_template(
            OPERATOR, self.org["id"], "Newsletter", "email", 1, 2048)
        self.assertEqual(template["id"], "tmpl-1")
        self.assertEqual(template["size_bytes"], 2048)
        with self.assertRaises(TypeError):
            self.ext.register_template(
                OPERATOR, self.org["id"], "Newsletter", "email", 2,
                2048, body="<html>...</html>")
        with self.assertRaises(ValidationError):
            self.ext.register_template(
                OPERATOR, self.org["id"], "Newsletter", "email", 1,
                1024)
        with self.assertRaises(ValidationError):
            self.ext.register_template(
                OPERATOR, self.org["id"], "Other", "email", 0, 1024)

    def test_preferences_latest_wins_and_absence_is_absent(self):
        self.ext.record_preference(
            OPERATOR, self.lst["id"], CONTACT_A, "frequency",
            "weekly")
        self.ext.record_preference(
            OPERATOR, self.lst["id"], CONTACT_A, "frequency",
            "monthly")
        self.ext.record_preference(
            OPERATOR, self.lst["id"], CONTACT_A, "channel",
            "email only")
        current = self.ext.current_preferences(
            ADMIN, self.lst["id"], CONTACT_A)
        self.assertEqual(current, {"frequency": "monthly",
                                   "channel": "email only"})
        self.assertNotIn("topic", current)
        with self.assertRaises(ValidationError):
            self.ext.record_preference(
                OPERATOR, self.lst["id"], CONTACT_A, "timing",
                "mornings")
        with self.assertRaises(ValidationError):
            self.ext.record_preference(
                OPERATOR, self.lst["id"], "a@example.com",
                "frequency", "weekly")


class AccessAndAuditTests(unittest.TestCase):
    def test_viewer_writes_are_denied_and_consume_no_id(self):
        store, _audit, ext = make_ext()
        org = make_org(store)
        with self.assertRaises(PermissionDenied):
            ext.register_ai_request(VIEWER, org["id"], "MODEL-REF-1",
                                    "draft")
        record = ext.register_ai_request(OPERATOR, org["id"],
                                         "MODEL-REF-1", "draft")
        self.assertEqual(record["id"], "aireq-1")

    def test_extension_mutations_land_on_the_core_audit_log(self):
        store, audit, ext = make_ext()
        org = make_org(store)
        ext.register_ai_request(OPERATOR, org["id"], "MODEL-REF-1",
                                "draft")
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_register_ai_request", actions)

    def test_failed_audit_write_rolls_back_the_record(self):
        store, audit, ext = make_ext()
        org = make_org(store)

        class RaisingAudit:
            def record(self, actor, action, target, details=None):
                raise RuntimeError("audit unavailable")

            def entries(self):
                return []

        store.audit = RaisingAudit()
        with self.assertRaises(RuntimeError):
            ext.register_ai_request(OPERATOR, org["id"],
                                    "MODEL-REF-1", "draft")
        self.assertEqual(ext.list_ai_requests(ADMIN), [])
        store.audit = AuditLog()
        record = ext.register_ai_request(OPERATOR, org["id"],
                                         "MODEL-REF-1", "draft")
        self.assertEqual(record["id"], "aireq-1")


class ShapeScanTests(unittest.TestCase):
    def test_no_tier_or_forbidden_key_on_the_extension_surface(self):
        store, _audit, ext = make_ext()
        org = make_org(store)
        opp = make_opportunity(store, org)
        campaign, lst, seg = make_campaign(store, org)
        request = ext.register_ai_request(
            OPERATOR, org["id"], "MODEL-REF-1", "draft support",
            opportunity_id=opp["id"])
        ext.record_ai_report(OPERATOR, request["id"], "completed",
                             result_ref="RESULT-REF-1")
        ext.record_ai_evaluation(OPERATOR, request["id"], 87)
        ext.register_agent_definition(OPERATOR, org["id"], "Agent",
                                      ["watch feeds"])
        feed = ext.register_discovery_feed(
            OPERATOR, org["id"], "SAM feed", "sam.gov")
        ext.record_discovery_report(OPERATOR, feed["id"], 42)
        ext.record_intelligence_report(
            OPERATOR, org["id"], "IDIQ market", "note", "SRC-1")
        ext.record_forecast(OPERATOR, org["id"], "FY27", "FY27", 5,
                            "SRC-2")
        gen = ext.request_proposal_generation(
            OPERATOR, opp["id"], "Volume I", "section")
        ext.record_generation_report(OPERATOR, gen["id"], "done")
        workflow = store.create_workflow(
            OPERATOR, org["id"], "Digest", "new opportunity posted")
        wexec = ext.request_workflow_execution(
            OPERATOR, workflow["id"], {"window_days": 7})
        ext.record_workflow_execution_report(
            OPERATOR, wexec["id"], "ran externally")
        segreq = ext.request_segmentation(
            OPERATOR, seg["id"], [{"field": "role", "value": "pm"}])
        ext.record_segmentation_report(OPERATOR, segreq["id"], 288)
        send = ext.request_send(OPERATOR, campaign["id"])
        ext.record_transport_receipt(OPERATOR, send["id"], 900, 12,
                                     3)
        ext.register_handling_rule(OPERATOR, org["id"],
                                   "bounced_outcome",
                                   "record_suppression")
        store.record_delivery(OPERATOR, campaign["id"], CONTACT_A,
                              "bounced", OCCURRED)
        ext.record_handling(OPERATOR, lst["id"], CONTACT_A,
                            "bounced_outcome", "reviewed_no_action",
                            campaign_id=campaign["id"])
        ext.register_template(OPERATOR, org["id"], "Newsletter",
                              "email", 1, 2048)
        ext.record_preference(OPERATOR, lst["id"], CONTACT_A,
                              "frequency", "weekly")
        everything = {
            "ai_requests": ext.list_ai_requests(ADMIN),
            "ai_reports": ext.list_ai_reports(ADMIN),
            "ai_evaluations": ext.list_ai_evaluations(ADMIN),
            "agent_definitions": ext.list_agent_definitions(ADMIN),
            "feeds": ext.list_discovery_feeds(ADMIN),
            "discovery_reports": ext.list_discovery_reports(ADMIN),
            "intelligence": ext.list_intelligence_reports(ADMIN),
            "forecasts": ext.list_forecasts(ADMIN),
            "generation_requests": ext.list_generation_requests(
                ADMIN),
            "generation_reports": ext.list_generation_reports(ADMIN),
            "workflow_executions":
                ext.list_workflow_execution_requests(ADMIN),
            "workflow_execution_reports":
                ext.list_workflow_execution_reports(ADMIN),
            "segmentation_requests":
                ext.list_segmentation_requests(ADMIN),
            "segmentation_reports":
                ext.list_segmentation_reports(ADMIN),
            "send_requests": ext.list_send_requests(ADMIN),
            "receipts": ext.list_transport_receipts(ADMIN),
            "handling_rules": ext.list_handling_rules(ADMIN),
            "handling_records": ext.list_handling_records(ADMIN),
            "templates": ext.list_templates(ADMIN),
            "preferences": ext.list_preferences(ADMIN),
            "market_view": ext.market_view(ADMIN),
            "pending": ext.pending_handling(ADMIN),
            "current_preferences": ext.current_preferences(
                ADMIN, lst["id"], CONTACT_A),
            "summary": ext.extension_summary(ADMIN),
        }
        scan_keys(everything)


def canonical_pending_queue_drains_when_handled(ext, store, campaign,
                                                contact_list):
    """The batch's canonical expectation, stated once: a bounced
    delivery enters the derived handling queue, and recording the
    handling decision for it drains exactly that item. Raises
    AssertionError when either arm fails."""
    store.record_delivery(OPERATOR, campaign["id"], CONTACT_A,
                          "bounced", OCCURRED)
    pending = ext.pending_handling(ADMIN)
    assert any(p["contact_ref"] == CONTACT_A
               and p["trigger"] == "bounced_outcome"
               for p in pending), (
        "a bounced delivery did not enter the handling queue")
    ext.record_handling(OPERATOR, contact_list["id"], CONTACT_A,
                        "bounced_outcome", "suppression_recorded",
                        campaign_id=campaign["id"])
    pending = ext.pending_handling(ADMIN)
    assert not any(p["contact_ref"] == CONTACT_A
                   and p["trigger"] == "bounced_outcome"
                   for p in pending), (
        "a handled item stayed in the handling queue; the "
        "coverage check did not discriminate")


def _mutant_covered(covered_keys, key):
    """Mutant seam: every candidate counts as handled, so the
    queue is always empty."""
    return True


class NegativeControlTests(unittest.TestCase):
    def _setup(self):
        store, _audit, ext = make_ext()
        org = make_org(store)
        campaign, contact_list, _seg = make_campaign(store, org)
        return ext, store, campaign, contact_list

    def test_canonical_check_passes_on_the_real_surface(self):
        ext, store, campaign, contact_list = self._setup()
        canonical_pending_queue_drains_when_handled(
            ext, store, campaign, contact_list)

    def test_canonical_check_fails_on_the_mutant(self):
        ext, store, campaign, contact_list = self._setup()
        original = extensions_module._handling_covered
        extensions_module._handling_covered = _mutant_covered
        try:
            with self.assertRaises(AssertionError):
                canonical_pending_queue_drains_when_handled(
                    ext, store, campaign, contact_list)
        finally:
            extensions_module._handling_covered = original

    def test_queue_is_trigger_specific_on_the_real_surface(self):
        """The other arm discriminates too: a ``delivered`` outcome
        for the same contact raises no queue item, and releasing a
        complaint suppression removes its item — the queue tracks
        unhandled bounce/complaint facts, not contacts."""
        ext, store, campaign, contact_list = self._setup()
        store.record_delivery(OPERATOR, campaign["id"], CONTACT_A,
                              "delivered", OCCURRED)
        self.assertEqual(ext.pending_handling(ADMIN), [])
        suppression = store.record_suppression(
            OPERATOR, contact_list["id"], CONTACT_B, "complaint")
        self.assertEqual(len(ext.pending_handling(ADMIN)), 1)
        store.release_suppression(OPERATOR, suppression["id"])
        self.assertEqual(ext.pending_handling(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
