"""Final GAPS batch tests -- Communication L1 singleton (Group 37).

Traces to: the 8 open entries of GAPS.md section "Singleton 37 --
Communication L1 (1 fork)" (inventory idx 381-388), worked under
gaps-batch/DECISION.md. Every test pins a part of the extension
surface in ``src/comm/extensions.py`` (``CommExtensions``):

- idx 381 campaign orchestration -- reference: definitions as data,
  lifecycle state records, send records binding core messages;
  the registry never executes and dispatches nothing.
- idx 382 audience segmentation -- built: criteria as data,
  membership derived at read over the core directory.
- idx 383 customer profiles -- built: profile records keyed by
  caller-supplied opaque refs, caller-asserted links; identity
  resolution is NOT performed.
- idx 384 real-time interaction management -- built (records
  form): session records with verbatim reported labels; nothing
  is live and no decisioning happens here.
- idx 385 workflow / BPM -- reference: definitions as data plus
  reported outcomes; pinned to change no core record.
- idx 386 reporting / analytics -- built: deterministic counts
  derived at read over core + extension records; nothing stored.
- idx 387 real channel execution -- reference: configuration and
  execution records carrying reference_transport labels; pinned
  to change no core delivery.
- idx 388 managed-service operations -- reference: operation
  report records; counts derived at read.

Cross-cutting pins: extension records never hold message content
(no subject/body/content key anywhere, recursively); failed
operations consume no extension ids; denied writes are audited
with a ``:denied`` suffix; successful mutations are audited with
an ``ext_`` prefix.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError
from comm.extensions import CommExtensions


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class _BatchBase(unittest.TestCase):
    """Fixture: canonical store (Dana contact, team group, email
    channel) plus a second and third contact for segmentation."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()
        self.ext = CommExtensions(self.store)
        self.erin = self.store.create_contact(
            "Erin Example", {"sms": "+1-555-0200"}, OPERATOR)
        self.frank = self.store.create_contact(
            "Frank North", {"email": "frank@example.com"}, OPERATOR)

    def _compose(self, **kw):
        kw.setdefault("subject", "Hi")
        kw.setdefault("body", "Body")
        kw.setdefault("contact_ids", [self.contact["id"]])
        kw.setdefault("channel_kinds", ["email"])
        return self.store.compose_message(OPERATOR, **kw)


class TestCampaignOrchestration(_BatchBase):
    """Gap idx 381 -- campaign orchestration engine (reference)."""

    def test_define_campaign_shape_and_labels(self):
        campaign = self.ext.define_campaign(
            "Spring drive", OPERATOR,
            steps=[{"label": "draft", "channel_kind": "email"},
                   {"label": "send"}],
            channel_kinds=["email", "sms"])
        self.assertEqual(campaign["id"], "cmp-1")
        self.assertEqual(campaign["name"], "Spring drive")
        self.assertEqual(campaign["steps"][0]["channel_kind"], "email")
        self.assertEqual(campaign["channel_kinds"], ["email", "sms"])
        self.assertIsNone(campaign["template_id"])
        self.assertTrue(campaign["reference_stub"])
        self.assertTrue(campaign["definition_only"])
        self.assertFalse(campaign["orchestrated_here"])
        self.assertFalse(campaign["executed_here"])
        self.assertEqual(campaign["created_by"], "bob")

    def test_define_campaign_template_binding_validated(self):
        template = self.store.create_template("t", "S {x}", "B {x}",
                                              OPERATOR)
        campaign = self.ext.define_campaign(
            "T", OPERATOR, template_id=template["id"])
        self.assertEqual(campaign["template_id"], template["id"])
        with self.assertRaises(NotFoundError):
            self.ext.define_campaign("T2", OPERATOR,
                                     template_id="tpl-999")

    def test_define_campaign_bad_step_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.define_campaign(
                "Bad", OPERATOR,
                steps=[{"label": "x", "channel_kind": "postal"}])
        with self.assertRaises(ValidationError):
            self.ext.define_campaign(
                "Bad", OPERATOR, steps=[{"label": "x", "bogus": "y"}])
        campaign = self.ext.define_campaign("Good", OPERATOR)
        self.assertEqual(campaign["id"], "cmp-1")

    def test_campaign_lifecycle_derived_at_read(self):
        campaign = self.ext.define_campaign("Life", OPERATOR)
        view = self.ext.campaign_view(campaign["id"], OPERATOR)
        self.assertEqual(view["current_state"], "not_started")
        self.assertEqual(view["state_count"], 0)
        # Stored definition carries no derived key.
        stored = self.ext.get_campaign(campaign["id"], OPERATOR)
        self.assertNotIn("current_state", stored)
        self.assertNotIn("state_count", stored)
        self.ext.record_campaign_state(campaign["id"], "scheduled",
                                       OPERATOR)
        self.ext.record_campaign_state(campaign["id"], "active", OPERATOR)
        view = self.ext.campaign_view(campaign["id"], OPERATOR)
        self.assertEqual(view["current_state"], "active")
        self.assertEqual(view["state_count"], 2)
        with self.assertRaises(ValidationError):
            self.ext.record_campaign_state(campaign["id"], "bogus",
                                           OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_campaign_state("cmp-999", "active", OPERATOR)

    def test_campaign_send_binds_message_and_dispatches_nothing(self):
        campaign = self.ext.define_campaign("Send", OPERATOR)
        message = self._compose()
        send = self.ext.record_campaign_send(campaign["id"],
                                             message["id"], OPERATOR)
        self.assertTrue(send["reference_stub"])
        self.assertTrue(send["reference_transport"])
        self.assertFalse(send["transmitted_here"])
        self.assertFalse(send["dispatched_by_extension"])
        # The core delivery is untouched: still queued, no receipt.
        deliveries = self.store.list_deliveries(message_id=message["id"])
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0]["status"], "queued")
        self.assertIsNone(deliveries[0]["receipt"])
        view = self.ext.campaign_view(campaign["id"], OPERATOR)
        self.assertEqual(view["send_count"], 1)
        with self.assertRaises(NotFoundError):
            self.ext.record_campaign_send(campaign["id"], "msg-999",
                                          OPERATOR)

    def test_campaign_write_denied_for_viewer_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_campaign("Nope", VIEWER)
        denied = [e for e in self.store.audit.entries()
                  if e["action"] == "ext_campaign_define:denied"]
        self.assertEqual(len(denied), 1)
        # A successful write is audited with the ext_ prefix.
        self.ext.define_campaign("Ok", OPERATOR)
        done = [e for e in self.store.audit.entries()
                if e["action"] == "ext_campaign_define"]
        self.assertEqual(len(done), 1)


class TestAudienceSegmentation(_BatchBase):
    """Gap idx 382 -- audience segmentation engine (built)."""

    def test_segment_by_channel_kind(self):
        segment = self.ext.define_segment(
            "Email reachable", [{"kind": "has_channel_kind",
                                 "value": "email"}], OPERATOR)
        self.assertEqual(segment["id"], "seg-1")
        self.assertEqual(segment["audience_source"], "core_directory")
        self.assertFalse(segment["external_audience_here"])
        view = self.ext.segment_view(segment["id"], OPERATOR)
        self.assertEqual(view["member_contact_ids"],
                         [self.contact["id"], self.frank["id"]])
        self.assertEqual(view["member_count"], 2)

    def test_segment_by_group_and_name(self):
        by_group = self.ext.define_segment(
            "Team", [{"kind": "in_group", "value": self.group["id"]}],
            OPERATOR)
        view = self.ext.segment_view(by_group["id"], OPERATOR)
        self.assertEqual(view["member_contact_ids"], [self.contact["id"]])
        by_name = self.ext.define_segment(
            "North", [{"kind": "name_contains", "value": "NORTH"}],
            OPERATOR)
        view = self.ext.segment_view(by_name["id"], OPERATOR)
        self.assertEqual(view["member_contact_ids"], [self.frank["id"]])

    def test_segment_criteria_are_anded(self):
        segment = self.ext.define_segment(
            "Team by SMS",
            [{"kind": "has_channel_kind", "value": "sms"},
             {"kind": "in_group", "value": self.group["id"]}],
            OPERATOR)
        view = self.ext.segment_view(segment["id"], OPERATOR)
        # Erin has SMS but is not in the group; only Dana matches both.
        self.assertEqual(view["member_contact_ids"], [self.contact["id"]])

    def test_segment_stored_record_has_no_derived_keys(self):
        segment = self.ext.define_segment(
            "S", [{"kind": "has_channel_kind", "value": "sms"}], OPERATOR)
        stored = self.ext.get_segment(segment["id"], OPERATOR)
        self.assertEqual(
            set(stored),
            {"id", "name", "criteria", "audience_source",
             "external_audience_here", "created_by", "created_utc"})

    def test_segment_validation_and_no_id_on_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.define_segment("Bad", [], OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.define_segment(
                "Bad", [{"kind": "has_channel_kind", "value": "postal"}],
                OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.define_segment(
                "Bad", [{"kind": "in_group", "value": "grp-999"}], OPERATOR)
        segment = self.ext.define_segment(
            "Good", [{"kind": "name_contains", "value": "a"}], OPERATOR)
        self.assertEqual(segment["id"], "seg-1")
        with self.assertRaises(PermissionDenied):
            self.ext.define_segment(
                "Nope", [{"kind": "name_contains", "value": "a"}], VIEWER)


class TestCustomerProfiles(_BatchBase):
    """Gap idx 383 -- customer profile store (built); no resolution."""

    def test_create_profile_shape_and_labels(self):
        profile = self.ext.create_profile(
            "cust-001", OPERATOR, contact_ids=[self.contact["id"]],
            attribute_labels=["newsletter", "donor"])
        self.assertEqual(profile["id"], "prf-1")
        self.assertEqual(profile["profile_ref"], "cust-001")
        self.assertEqual(profile["contact_ids"], [self.contact["id"]])
        self.assertEqual(profile["attribute_labels"],
                         ["newsletter", "donor"])
        self.assertFalse(profile["resolved_here"])
        self.assertFalse(profile["identity_resolution_performed"])
        self.assertFalse(profile["merged_here"])

    def test_duplicate_profile_ref_rejected_no_id_consumed(self):
        self.ext.create_profile("cust-001", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.create_profile("cust-001", OPERATOR)
        second = self.ext.create_profile("cust-002", OPERATOR)
        self.assertEqual(second["id"], "prf-2")

    def test_profile_links_and_derived_contact_set(self):
        profile = self.ext.create_profile(
            "cust-001", OPERATOR, contact_ids=[self.contact["id"]])
        link = self.ext.record_profile_link(
            profile["id"], self.erin["id"], OPERATOR,
            link_label="household")
        self.assertEqual(link["id"], "plk-1")
        self.assertTrue(link["asserted_by_caller"])
        self.assertFalse(link["resolved_here"])
        view = self.ext.profile_view(profile["id"], OPERATOR)
        self.assertEqual(view["all_contact_ids"],
                         [self.contact["id"], self.erin["id"]])
        self.assertEqual(view["contact_count"], 2)
        self.assertEqual(view["link_count"], 1)
        # The stored profile record itself is unchanged by links.
        stored = self.ext.get_profile(profile["id"], OPERATOR)
        self.assertEqual(stored["contact_ids"], [self.contact["id"]])
        self.assertNotIn("all_contact_ids", stored)

    def test_profile_link_validation(self):
        profile = self.ext.create_profile("cust-001", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_profile_link(profile["id"], "ct-999", OPERATOR)
        self.ext.record_profile_link(profile["id"], self.erin["id"],
                                     OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_profile_link(profile["id"], self.erin["id"],
                                         OPERATOR)


class TestRealTimeInteractions(_BatchBase):
    """Gap idx 384 -- real-time interaction management (records form)."""

    def test_record_interaction_shape_and_labels(self):
        record = self.ext.record_interaction(
            self.contact["id"], "email", OPERATOR,
            decision_label="offer:A", outcome_label="opened",
            interaction_ref="sess-9",
            occurred_utc="2026-11-01T10:00:00+00:00")
        self.assertEqual(record["id"], "int-1")
        self.assertEqual(record["decision_label"], "offer:A")
        self.assertFalse(record["live_here"])
        self.assertFalse(record["decisioning_here"])
        self.assertFalse(record["decided_here"])

    def test_interaction_current_outcome_derived(self):
        record = self.ext.record_interaction(
            self.contact["id"], "sms", OPERATOR, outcome_label="delivered")
        view = self.ext.interaction_view(record["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "delivered")
        self.assertEqual(view["outcome_count"], 0)
        self.ext.record_interaction_outcome(record["id"], "clicked",
                                            OPERATOR)
        self.ext.record_interaction_outcome(record["id"], "converted",
                                            OPERATOR)
        view = self.ext.interaction_view(record["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "converted")
        self.assertEqual(view["outcome_count"], 2)

    def test_interaction_unreported_outcome(self):
        record = self.ext.record_interaction(self.erin["id"], "push",
                                             OPERATOR)
        view = self.ext.interaction_view(record["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "unreported")

    def test_interaction_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_interaction(self.contact["id"], "postal",
                                        OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_interaction("ct-999", "email", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_interaction(self.contact["id"], "email",
                                        OPERATOR, occurred_utc="not-a-date")


class TestWorkflowBpm(_BatchBase):
    """Gap idx 385 -- workflow / BPM engine (reference)."""

    def test_define_workflow_shape_and_labels(self):
        workflow = self.ext.define_workflow(
            "Campaign approval",
            [{"label": "draft"},
             {"label": "approve", "approver_role": "admin"},
             {"label": "launch"}], OPERATOR)
        self.assertEqual(workflow["id"], "wfl-1")
        self.assertEqual(workflow["steps"][1]["approver_role"], "admin")
        self.assertTrue(workflow["reference_stub"])
        self.assertTrue(workflow["definition_only"])
        self.assertFalse(workflow["executed_here"])
        self.assertFalse(workflow["approvals_enforced_here"])

    def test_workflow_registry_never_executes(self):
        before = self.store.list_messages()
        before_contacts = self.store.list_contacts()
        workflow = self.ext.define_workflow(
            "W", [{"label": "approve", "approver_role": "admin"}],
            OPERATOR)
        outcome = self.ext.record_workflow_outcome(
            workflow["id"], "reported_approved", OPERATOR,
            step_label="approve")
        self.assertTrue(outcome["reference_stub"])
        self.assertTrue(outcome["reported_by_caller"])
        self.assertFalse(outcome["executed_here"])
        # Defining and reporting changed no core record.
        self.assertEqual(self.store.list_messages(), before)
        self.assertEqual(self.store.list_contacts(), before_contacts)
        view = self.ext.workflow_view(workflow["id"], OPERATOR)
        self.assertEqual(view["outcome_count"], 1)

    def test_workflow_requires_steps(self):
        with self.assertRaises(ValidationError):
            self.ext.define_workflow("Empty", [], OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_workflow_outcome("wfl-999", "x", OPERATOR)


class TestReportingAnalytics(_BatchBase):
    """Gap idx 386 -- reporting / analytics engines (built)."""

    def test_report_summary_counts(self):
        summary = self.ext.report_summary(OPERATOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["contacts"], 3)
        self.assertEqual(summary["messages"], 0)
        message = self._compose()
        self.store.dispatch_due(OPERATOR)
        summary = self.ext.report_summary(OPERATOR)
        self.assertEqual(summary["messages"], 1)
        self.assertEqual(summary["deliveries"], 1)
        self.assertEqual(summary["deliveries_by_status"]["delivered"], 1)
        self.assertEqual(summary["deliveries_by_status"]["queued"], 0)
        self.assertEqual(message["id"], "msg-1")

    def test_report_summary_is_derived_not_stored(self):
        first = self.ext.report_summary(OPERATOR)
        self.assertEqual(first["campaigns"], 0)
        self.ext.define_campaign("Later", OPERATOR)
        second = self.ext.report_summary(OPERATOR)
        self.assertEqual(second["campaigns"], 1)

    def test_campaign_effectiveness_derived(self):
        campaign = self.ext.define_campaign("Eff", OPERATOR)
        message = self._compose()
        self.ext.record_campaign_send(campaign["id"], message["id"],
                                      OPERATOR)
        eff = self.ext.campaign_effectiveness(campaign["id"], OPERATOR)
        self.assertEqual(eff["deliveries"], 1)
        self.assertEqual(eff["deliveries_by_status"]["queued"], 1)
        self.store.dispatch_due(OPERATOR)
        eff = self.ext.campaign_effectiveness(campaign["id"], OPERATOR)
        self.assertEqual(eff["deliveries_by_status"]["delivered"], 1)
        self.assertEqual(eff["message_ids"], [message["id"]])
        with self.assertRaises(NotFoundError):
            self.ext.campaign_effectiveness("cmp-999", OPERATOR)


class TestRealChannelExecution(_BatchBase):
    """Gap idx 387 -- real channel execution (reference)."""

    def test_configure_execution_channel_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.configure_execution_channel("email", "provider-x",
                                                 OPERATOR)
        config = self.ext.configure_execution_channel(
            "email", "provider-x", ADMIN)
        self.assertEqual(config["id"], "exc-1")
        self.assertTrue(config["reference_stub"])
        self.assertTrue(config["reference_transport"])
        self.assertFalse(config["real_channel_here"])
        self.assertFalse(config["transmitted_here"])

    def test_execution_record_changes_no_core_delivery(self):
        config = self.ext.configure_execution_channel(
            "sms", "provider-y", ADMIN)
        message = self.store.compose_message(
            OPERATOR, subject="S", body="B",
            contact_ids=[self.contact["id"]], channel_kinds=["sms"])
        record = self.ext.record_execution(
            config["id"], OPERATOR, message_id=message["id"])
        self.assertEqual(record["status"], "recorded_reference_only")
        self.assertTrue(record["reference_transport"])
        self.assertFalse(record["transmitted_here"])
        self.assertFalse(record["fulfilled_here"])
        deliveries = self.store.list_deliveries(message_id=message["id"])
        self.assertEqual(deliveries[0]["status"], "queued")
        self.assertIsNone(deliveries[0]["receipt"])
        view = self.ext.execution_channel_view(config["id"], OPERATOR)
        self.assertEqual(view["execution_count"], 1)

    def test_postal_execution_with_fulfillment_ref(self):
        config = self.ext.configure_execution_channel(
            "postal", "print-house", ADMIN)
        record = self.ext.record_execution(
            config["id"], OPERATOR, fulfillment_ref="mail-batch-7")
        self.assertIsNone(record["message_id"])
        self.assertEqual(record["fulfillment_ref"], "mail-batch-7")
        with self.assertRaises(ValidationError):
            self.ext.configure_execution_channel("fax", "p", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_execution(config["id"], OPERATOR,
                                      message_id="msg-999")


class TestManagedServiceOperations(_BatchBase):
    """Gap idx 388 -- managed-service operations (reference)."""

    def test_operation_records_and_summary(self):
        record = self.ext.record_service_operation(
            "platform_backup", "reported_completed", OPERATOR)
        self.assertEqual(record["id"], "sop-1")
        self.assertTrue(record["reference_stub"])
        self.assertTrue(record["reported_by_caller"])
        self.assertFalse(record["hosted_here"])
        self.assertFalse(record["operated_here"])
        self.ext.record_service_operation(
            "platform_backup", "reported_completed", OPERATOR)
        self.ext.record_service_operation(
            "scaling_event", "reported_completed", OPERATOR)
        summary = self.ext.operations_summary(OPERATOR)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_operation"]["platform_backup"], 2)
        self.assertEqual(summary["by_outcome"]["reported_completed"], 3)

    def test_operation_write_denied_for_viewer(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_service_operation("x", "y", VIEWER)


class TestNoContentHeld(_BatchBase):
    """Cross-cutting: no extension record can hold message content."""

    def test_no_content_keys_anywhere(self):
        campaign = self.ext.define_campaign("C", OPERATOR)
        message = self._compose()
        self.ext.record_campaign_send(campaign["id"], message["id"],
                                      OPERATOR)
        segment = self.ext.define_segment(
            "S", [{"kind": "name_contains", "value": "a"}], OPERATOR)
        profile = self.ext.create_profile("p-1", OPERATOR)
        self.ext.record_interaction(self.contact["id"], "email",
                                    OPERATOR, outcome_label="opened")
        workflow = self.ext.define_workflow("W", [{"label": "s"}],
                                            OPERATOR)
        config = self.ext.configure_execution_channel("email", "prov",
                                                      ADMIN)
        self.ext.record_execution(config["id"], OPERATOR,
                                  message_id=message["id"])
        self.ext.record_service_operation("op", "done", OPERATOR)
        views = [
            self.ext.campaign_view(campaign["id"], OPERATOR),
            self.ext.segment_view(segment["id"], OPERATOR),
            self.ext.profile_view(profile["id"], OPERATOR),
            self.ext.workflow_view(workflow["id"], OPERATOR),
            self.ext.execution_channel_view(config["id"], OPERATOR),
            self.ext.report_summary(OPERATOR),
            self.ext.operations_summary(OPERATOR),
        ]
        forbidden = {"subject", "body", "content", "audio", "media"}
        for view in views:
            self.assertFalse(forbidden & _all_keys(view),
                             "content-shaped key in %r" % (view,))


class _MatchAllExtensions(CommExtensions):
    """Mutant: the criteria seam waves every contact through."""

    @staticmethod
    def _criteria_match(criteria, contact, group_members):
        return True


class TestNegativeControlSegmentMembership(_BatchBase):
    """Fresh negative control for the batch: segment membership.

    The traced claim: **segment membership is the contacts for
    which every recorded criterion holds** -- derived at read over
    the core directory by the seam ``CommExtensions._criteria_match``
    (AND semantics). The mutant above replaces the seam with a
    wave-through (every contact matches), so a segment defined by
    a selective criterion would report the whole directory.

    Each canonical case asserts three things, per the house
    pattern: (1) the canonical expectation from the real
    implementation, (2) the mutant would NOT produce it, and
    (3) a literal assertRaises(AssertionError) showing that
    treating the mutant's outcome as the expected outcome fails.
    """

    def _both(self, criteria):
        segment = self.ext.define_segment("NC", criteria, OPERATOR)
        canonical = self.ext.segment_view(segment["id"],
                                          OPERATOR)["member_contact_ids"]
        # The mutant wraps the same core store and shares the
        # canonical instance's extension records (extension state
        # lives in the wrapper); only the seam differs.
        mutant_ext = _MatchAllExtensions(self.store)
        mutant_ext._records = self.ext._records
        mutant_ext._order = self.ext._order
        mutant_ext._counters = self.ext._counters
        mutant = mutant_ext.segment_view(segment["id"],
                                         OPERATOR)["member_contact_ids"]
        return canonical, mutant

    def test_channel_kind_criterion_canonical_but_mutant_waves_all(self):
        canonical, mutant = self._both(
            [{"kind": "has_channel_kind", "value": "email"}])
        self.assertEqual(canonical,
                         [self.contact["id"], self.frank["id"]])
        self.assertEqual(mutant, [self.contact["id"], self.erin["id"],
                                  self.frank["id"]])
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, canonical)

    def test_anded_criteria_canonical_but_mutant_waves_all(self):
        canonical, mutant = self._both(
            [{"kind": "has_channel_kind", "value": "sms"},
             {"kind": "in_group", "value": self.group["id"]}])
        self.assertEqual(canonical, [self.contact["id"]])
        self.assertEqual(len(mutant), 3)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, canonical)


if __name__ == "__main__":
    unittest.main()
