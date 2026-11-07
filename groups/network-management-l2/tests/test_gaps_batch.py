"""Final GAPS batch — Singleton 51 extension surface.

Traces to: UNION-SPEC.md "Gaps — specified, not implemented"
(the eleven open entries of the GAPS.md section "Singleton 51 —
Network Management L2") and gaps-batch/DECISION.md (ratified
2026-11-07). Each test class pins one entry's records form or
labeled reference form, including its honesty labels; the
cross-cutting class pins access and the no-computed-value key
scan; the last class is the batch's fresh negative control for
the config-push state derivation.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from netmgmt.extensions import NetmgmtExtensions

FORBIDDEN_KEY_PARTS = ("score", "rating", "health", "optimization")


def _all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _all_keys(value)


def make_extensions():
    """Fresh store + canonical org/network/device + the extension surface."""
    store, org = H.make_store()
    network, device = H.make_estate(store, org)
    H.make_telemetry(store, org, device)
    return NetmgmtExtensions(store), store, org, network, device


def make_push(ext, store, org, network, device=None):
    """A core change (optionally targeting the device) + a push record."""
    kwargs = {}
    if device is not None:
        kwargs["device_id"] = device["id"]
    change = H.make_change(store, org, network, **kwargs)
    push = ext.create_config_push(H.MEMBER, org["id"], change["id"])
    return change, push


class TestRecommendations(unittest.TestCase):
    """Optimization entry: recorded recommendations, nothing computed."""

    def test_record_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        record = ext.create_recommendation(
            H.MEMBER, org["id"], network["id"], "Review HQ throughput",
            "telemetry_review", detail_ref="REPORT-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "org_id", "network_id", "title", "basis", "detail_ref",
             "computed_here", "applied_here", "created_by", "created_utc"})
        self.assertEqual(record["id"], "opt-1")
        self.assertIs(record["computed_here"], False)
        self.assertIs(record["applied_here"], False)

    def test_invalid_basis_rejected_and_consumes_no_id(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_recommendation(
                H.MEMBER, org["id"], network["id"], "Nope", "magic")
        record = ext.create_recommendation(
            H.MEMBER, org["id"], network["id"], "Fine", "manual_review")
        self.assertEqual(record["id"], "opt-1")

    def test_network_in_other_org_rejected(self):
        ext, store, org, network, device = make_extensions()
        org2 = store.create_organization(H.MEMBER, "AGENCY-2", "Agency Two")
        net2 = H.make_network(store, org2, ref="NET-OTHER")
        with self.assertRaises(ValidationError):
            ext.create_recommendation(
                H.MEMBER, org["id"], net2["id"], "Cross-org", "manual_review")


class TestModelProfiles(unittest.TestCase):
    """Intelligence entry: model profiles + verbatim reported outputs."""

    def test_profile_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        profile = ext.create_model_profile(
            H.MEMBER, org["id"], network["id"], "Anomaly watcher",
            "anomaly_detection")
        self.assertEqual(
            set(profile.keys()),
            {"id", "org_id", "network_id", "name", "model_kind",
             "reference_stub", "inference_here", "created_by", "created_utc"})
        self.assertIs(profile["reference_stub"], True)
        self.assertIs(profile["inference_here"], False)
        view = ext.get_model_profile(H.MEMBER, profile["id"])
        self.assertEqual(view["observation_count"], 0)

    def test_observation_record_and_derived_count(self):
        ext, store, org, network, device = make_extensions()
        profile = ext.create_model_profile(
            H.MEMBER, org["id"], network["id"], "Insight engine",
            "insight_generation")
        observation = ext.record_model_observation(
            H.MEMBER, org["id"], profile["id"], "unusual-egress",
            detail_ref="OBS-1")
        self.assertEqual(
            set(observation.keys()),
            {"id", "org_id", "profile_id", "label", "detail_ref",
             "reference_stub", "computed_here", "created_by", "created_utc"})
        self.assertIs(observation["computed_here"], False)
        view = ext.get_model_profile(H.MEMBER, profile["id"])
        self.assertEqual(view["observation_count"], 1)

    def test_lookup_filters_are_exact_match(self):
        ext, store, org, network, device = make_extensions()
        net2 = H.make_network(store, org, ref="NET-BRANCH")
        ext.create_model_profile(H.MEMBER, org["id"], network["id"],
                                 "A", "anomaly_detection")
        ext.create_model_profile(H.MEMBER, org["id"], net2["id"],
                                 "B", "classification")
        by_kind = ext.find_model_profiles(
            H.MEMBER, org["id"], model_kind="classification")
        self.assertEqual([p["name"] for p in by_kind], ["B"])
        by_network = ext.find_model_profiles(
            H.MEMBER, org["id"], network_id=network["id"])
        self.assertEqual([p["name"] for p in by_network], ["A"])
        all_profiles = ext.find_model_profiles(H.MEMBER, org["id"])
        self.assertEqual([p["name"] for p in all_profiles], ["A", "B"])

    def test_invalid_model_kind_rejected(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_model_profile(
                H.MEMBER, org["id"], network["id"], "Nope", "learning")


class TestConfigPush(unittest.TestCase):
    """Push entry: change-linked records; recording one touches nothing."""

    def test_push_shape_derives_recorded_state(self):
        ext, store, org, network, device = make_extensions()
        change, push = make_push(ext, store, org, network, device)
        self.assertEqual(
            set(push.keys()),
            {"id", "org_id", "change_id", "network_id", "device_id",
             "applied_here", "created_by", "created_utc",
             "current_state", "outcome_count"})
        self.assertIs(push["applied_here"], False)
        self.assertEqual(push["current_state"], "recorded")
        self.assertEqual(push["outcome_count"], 0)
        stored = ext._pushes[push["id"]]
        self.assertNotIn("current_state", stored)
        self.assertNotIn("outcome_count", stored)

    def test_outcome_states_derive_latest(self):
        ext, store, org, network, device = make_extensions()
        change, push = make_push(ext, store, org, network, device)
        outcome = ext.record_push_outcome(
            H.MEMBER, push["id"], "reported_failed", note="device refused")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "org_id", "push_id", "reported_state", "note",
             "created_by", "created_utc"})
        view = ext.get_config_push(H.MEMBER, push["id"])
        self.assertEqual(view["current_state"], "reported_failed")
        ext.record_push_outcome(H.MEMBER, push["id"], "reported_applied")
        view = ext.get_config_push(H.MEMBER, push["id"])
        self.assertEqual(view["current_state"], "reported_applied")
        self.assertEqual(view["outcome_count"], 2)

    def test_recording_push_changes_no_core_record(self):
        ext, store, org, network, device = make_extensions()
        change = H.make_change(store, org, network, device_id=device["id"])
        before = (
            dict(store._devices[device["id"]]),
            dict(store._networks[network["id"]]),
            dict(store._changes[change["id"]]),
        )
        push = ext.create_config_push(H.MEMBER, org["id"], change["id"])
        ext.record_push_outcome(H.MEMBER, push["id"], "reported_applied")
        after = (
            dict(store._devices[device["id"]]),
            dict(store._networks[network["id"]]),
            dict(store._changes[change["id"]]),
        )
        self.assertEqual(before, after)
        self.assertEqual(after[2]["status"], "requested")

    def test_push_requires_existing_change(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.create_config_push(H.MEMBER, org["id"], "chg-99")

    def test_invalid_outcome_state_rejected_and_no_id_consumed(self):
        ext, store, org, network, device = make_extensions()
        change, push = make_push(ext, store, org, network)
        with self.assertRaises(ValidationError):
            ext.record_push_outcome(H.MEMBER, push["id"], "applied")
        outcome = ext.record_push_outcome(
            H.MEMBER, push["id"], "reported_partial")
        self.assertEqual(outcome["id"], "out-1")


class TestFirmware(unittest.TestCase):
    """Firmware entry: version records + assignments, nothing deployed."""

    def test_firmware_and_assignment_shapes(self):
        ext, store, org, network, device = make_extensions()
        firmware = ext.create_firmware(
            H.MEMBER, org["id"], "switching", "v24.1", detail_ref="FW-REL-1")
        self.assertEqual(
            set(firmware.keys()),
            {"id", "org_id", "device_class", "version_label", "detail_ref",
             "created_by", "created_utc"})
        assignment = ext.assign_firmware(
            H.MEMBER, org["id"], firmware["id"], device["id"])
        self.assertEqual(
            set(assignment.keys()),
            {"id", "org_id", "firmware_id", "device_id", "deployed_here",
             "created_by", "created_utc", "current_state", "state_count"})
        self.assertIs(assignment["deployed_here"], False)
        self.assertEqual(assignment["current_state"], "recorded")

    def test_assignment_class_mismatch_rejected(self):
        ext, store, org, network, device = make_extensions()
        firmware = ext.create_firmware(H.MEMBER, org["id"], "wireless", "v9")
        with self.assertRaises(ValidationError):
            ext.assign_firmware(H.MEMBER, org["id"], firmware["id"],
                                device["id"])  # device is switching
        firmware2 = ext.create_firmware(H.MEMBER, org["id"], "switching", "v1")
        assignment = ext.assign_firmware(
            H.MEMBER, org["id"], firmware2["id"], device["id"])
        self.assertEqual(assignment["id"], "fwa-1")

    def test_assignment_state_derivation(self):
        ext, store, org, network, device = make_extensions()
        firmware = ext.create_firmware(H.MEMBER, org["id"], "switching", "v2")
        assignment = ext.assign_firmware(
            H.MEMBER, org["id"], firmware["id"], device["id"])
        ext.record_assignment_state(H.MEMBER, assignment["id"],
                                    "reported_pending")
        ext.record_assignment_state(H.MEMBER, assignment["id"],
                                    "reported_installed")
        view = ext.get_assignment(H.MEMBER, assignment["id"])
        self.assertEqual(view["current_state"], "reported_installed")
        self.assertEqual(view["state_count"], 2)


class TestTrafficPolicies(unittest.TestCase):
    """Traffic/SD-WAN entry: policy definitions as data, never enforced."""

    RULES = [{"name": "voice-first", "action": "prioritize",
              "match_ref": "TRAFFIC-VOICE"}]

    def test_definition_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        policy = ext.create_traffic_policy(
            H.MEMBER, org["id"], network["id"], "HQ SD-WAN", self.RULES)
        self.assertEqual(
            set(policy.keys()),
            {"id", "org_id", "network_id", "name", "rules",
             "evaluated_here", "enforced_here", "created_by", "created_utc",
             "current_state", "state_count"})
        self.assertIs(policy["evaluated_here"], False)
        self.assertIs(policy["enforced_here"], False)
        self.assertEqual(policy["current_state"], "unreported")

    def test_rules_deep_copied_at_boundary(self):
        ext, store, org, network, device = make_extensions()
        rules = [dict(self.RULES[0])]
        policy = ext.create_traffic_policy(
            H.MEMBER, org["id"], network["id"], "P", rules)
        rules[0]["action"] = "deny"
        rules.append({"name": "x", "action": "deny", "match_ref": "Y"})
        view = ext.get_traffic_policy(H.MEMBER, policy["id"])
        self.assertEqual(view["rules"], self.RULES)
        view["rules"][0]["action"] = "deny"
        again = ext.get_traffic_policy(H.MEMBER, policy["id"])
        self.assertEqual(again["rules"], self.RULES)

    def test_invalid_rule_rejected(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_traffic_policy(
                H.MEMBER, org["id"], network["id"], "P",
                [{"name": "r", "action": "block", "match_ref": "M"}])
        with self.assertRaises(ValidationError):
            ext.create_traffic_policy(
                H.MEMBER, org["id"], network["id"], "P", [])
        with self.assertRaises(ValidationError):
            ext.create_traffic_policy(
                H.MEMBER, org["id"], network["id"], "P",
                [{"name": "r", "action": "allow", "match_ref": "M",
                  "extra": 1}])

    def test_policy_state_records_derive_current(self):
        ext, store, org, network, device = make_extensions()
        policy = ext.create_traffic_policy(
            H.MEMBER, org["id"], network["id"], "P", self.RULES)
        ext.record_policy_state(H.MEMBER, org["id"], policy["id"],
                                "reported_active")
        ext.record_policy_state(H.MEMBER, org["id"], policy["id"],
                                "reported_degraded")
        view = ext.get_traffic_policy(H.MEMBER, policy["id"])
        self.assertEqual(view["current_state"], "reported_degraded")
        self.assertEqual(view["state_count"], 2)


class TestAutomationRuns(unittest.TestCase):
    """Automation entry: run references only; the registry never executes."""

    def test_run_reference_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        automation = H.make_automation(store, org)
        run = ext.record_automation_run(
            H.MEMBER, org["id"], automation["id"], "reported_completed",
            detail_ref="RUN-LOG-1")
        self.assertEqual(
            set(run.keys()),
            {"id", "org_id", "automation_id", "reported_status", "detail_ref",
             "reference_stub", "executed_here", "created_by", "created_utc"})
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["executed_here"], False)

    def test_recording_run_changes_no_core_record(self):
        ext, store, org, network, device = make_extensions()
        automation = H.make_automation(store, org)
        before_summary = store.organization_summary(H.MEMBER, org["id"])
        before_automation = dict(store._automations[automation["id"]])
        ext.record_automation_run(H.MEMBER, org["id"], automation["id"],
                                  "reported_failed")
        self.assertEqual(store.organization_summary(H.MEMBER, org["id"]),
                         before_summary)
        self.assertEqual(dict(store._automations[automation["id"]]),
                         before_automation)

    def test_invalid_run_status_rejected(self):
        ext, store, org, network, device = make_extensions()
        automation = H.make_automation(store, org)
        with self.assertRaises(ValidationError):
            ext.record_automation_run(H.MEMBER, org["id"], automation["id"],
                                      "completed")


class TestPageConfigs(unittest.TestCase):
    """Cloud app entry: page configurations as data, nothing served."""

    WIDGETS = [{"kind": "device_list", "title": "Devices"},
               {"kind": "alert_feed", "title": "Alerts"},
               {"kind": "device_list", "title": "Devices again"}]

    def test_page_shape_labels_and_derived_view(self):
        ext, store, org, network, device = make_extensions()
        page = ext.create_page_config(
            H.MEMBER, org["id"], "PAGE-HOME", "Home", self.WIDGETS)
        self.assertEqual(
            set(page.keys()),
            {"id", "org_id", "page_ref", "title", "widgets",
             "rendered_here", "served_here", "created_by", "created_utc",
             "widget_count", "widget_kinds"})
        self.assertIs(page["rendered_here"], False)
        self.assertIs(page["served_here"], False)
        self.assertEqual(page["widget_count"], 3)
        self.assertEqual(page["widget_kinds"], ["alert_feed", "device_list"])
        stored = ext._pages[page["id"]]
        self.assertNotIn("widget_count", stored)

    def test_duplicate_page_ref_rejected_and_no_id_consumed(self):
        ext, store, org, network, device = make_extensions()
        ext.create_page_config(H.MEMBER, org["id"], "PAGE-1", "One", [])
        with self.assertRaises(ValidationError):
            ext.create_page_config(H.MEMBER, org["id"], "PAGE-1", "Dup", [])
        page = ext.create_page_config(H.MEMBER, org["id"], "PAGE-2", "Two", [])
        self.assertEqual(page["id"], "pgc-2")

    def test_invalid_widget_rejected(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_page_config(
                H.MEMBER, org["id"], "PAGE-X", "X",
                [{"kind": "video_wall", "title": "Wall"}])


class TestProvisioningStub(unittest.TestCase):
    """Provisioning stub: references for devices not yet in inventory."""

    def test_reference_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        reference = ext.create_provisioning_reference(
            H.MEMBER, org["id"], network["id"], "DEV-NEW-1")
        self.assertEqual(
            set(reference.keys()),
            {"id", "org_id", "network_id", "device_ref", "detail_ref",
             "reference_stub", "provisioned_here", "created_by",
             "created_utc", "current_state", "state_count"})
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["provisioned_here"], False)
        self.assertEqual(reference["current_state"], "recorded")

    def test_provisioning_creates_no_core_device(self):
        ext, store, org, network, device = make_extensions()
        before = len(store.list_devices(H.MEMBER, org["id"]))
        ext.create_provisioning_reference(
            H.MEMBER, org["id"], network["id"], "DEV-NEW-9")
        self.assertEqual(len(store.list_devices(H.MEMBER, org["id"])), before)
        self.assertEqual(len(store._devices), before)

    def test_provisioning_state_derivation(self):
        ext, store, org, network, device = make_extensions()
        reference = ext.create_provisioning_reference(
            H.MEMBER, org["id"], network["id"], "DEV-NEW-2")
        ext.record_provisioning_state(H.MEMBER, org["id"], reference["id"],
                                      "reported_pending")
        ext.record_provisioning_state(H.MEMBER, org["id"], reference["id"],
                                      "reported_provisioned")
        view = ext.get_provisioning_reference(H.MEMBER, reference["id"])
        self.assertEqual(view["current_state"], "reported_provisioned")
        self.assertEqual(view["state_count"], 2)


class TestCollectionStub(unittest.TestCase):
    """Telemetry stub: collection references + reported receipts only."""

    def test_reference_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        reference = ext.create_collection_reference(
            H.MEMBER, org["id"], device["id"], "throughput", "5m")
        self.assertEqual(
            set(reference.keys()),
            {"id", "org_id", "device_id", "metric", "interval_label",
             "reference_stub", "reference_transport", "collected_here",
             "created_by", "created_utc"})
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["reference_transport"], True)
        self.assertIs(reference["collected_here"], False)

    def test_receipt_counts_as_reported_and_no_core_telemetry(self):
        ext, store, org, network, device = make_extensions()
        reference = ext.create_collection_reference(
            H.MEMBER, org["id"], device["id"], "throughput", "5m")
        before = len(store.list_telemetry(H.MEMBER, device["id"]))
        receipt = ext.record_collection_receipt(
            H.MEMBER, org["id"], reference["id"], 12, "2026-06-01T08:00/09:00")
        self.assertEqual(receipt["records_reported"], 12)
        self.assertIs(receipt["collected_here"], False)
        self.assertEqual(len(store.list_telemetry(H.MEMBER, device["id"])),
                         before)

    def test_receipt_rejects_non_integer_count(self):
        ext, store, org, network, device = make_extensions()
        reference = ext.create_collection_reference(
            H.MEMBER, org["id"], device["id"], "throughput", "5m")
        for bad in (1.5, True, "12"):
            with self.assertRaises(ValidationError):
                ext.record_collection_receipt(
                    H.MEMBER, org["id"], reference["id"], bad, "w")


class TestAlertStubs(unittest.TestCase):
    """Alert stub: verbatim evaluations + transport receipts; alert intact."""

    def test_evaluation_shape_and_alert_untouched(self):
        ext, store, org, network, device = make_extensions()
        alert = H.make_alert(store, org, network_id=network["id"],
                             device_id=device["id"])
        before = dict(store._alerts[alert["id"]])
        evaluation = ext.record_alert_evaluation(
            H.MEMBER, org["id"], alert["id"], "confirmed")
        self.assertEqual(
            set(evaluation.keys()),
            {"id", "org_id", "alert_id", "verdict_label", "detail_ref",
             "reference_stub", "evaluated_here", "created_by", "created_utc"})
        self.assertIs(evaluation["evaluated_here"], False)
        self.assertEqual(dict(store._alerts[alert["id"]]), before)

    def test_delivery_shape_labels_and_alert_untouched(self):
        ext, store, org, network, device = make_extensions()
        alert = H.make_alert(store, org)
        before = dict(store._alerts[alert["id"]])
        delivery = ext.record_alert_delivery(
            H.MEMBER, org["id"], alert["id"], "email", "reported_delivered")
        self.assertEqual(
            set(delivery.keys()),
            {"id", "org_id", "alert_id", "channel", "reported_state",
             "reference_stub", "reference_transport", "delivered_here",
             "created_by", "created_utc"})
        self.assertIs(delivery["reference_transport"], True)
        self.assertIs(delivery["delivered_here"], False)
        self.assertEqual(dict(store._alerts[alert["id"]]), before)

    def test_delivery_invalid_channel_rejected(self):
        ext, store, org, network, device = make_extensions()
        alert = H.make_alert(store, org)
        with self.assertRaises(ValidationError):
            ext.record_alert_delivery(
                H.MEMBER, org["id"], alert["id"], "pager",
                "reported_delivered")


class TestConnectorStub(unittest.TestCase):
    """Connector stub: references naming external systems; nothing connects."""

    def test_connector_shape_and_labels(self):
        ext, store, org, network, device = make_extensions()
        connector = ext.create_connector_reference(
            H.MEMBER, org["id"], "Ticketing sync", "SYS-TICKETS")
        self.assertEqual(
            set(connector.keys()),
            {"id", "org_id", "name", "system_ref", "detail_ref",
             "reference_stub", "reference_transport", "connected_here",
             "created_by", "created_utc"})
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["reference_transport"], True)
        self.assertIs(connector["connected_here"], False)


class TestAccessAndSurface(unittest.TestCase):
    """Cross-cutting: founding RBAC + membership, counts-only summary,
    and the no-computed-value recursive key scan over extension views."""

    def test_viewer_member_cannot_write_and_denial_is_audited(self):
        ext, store, org, network, device = make_extensions()
        store.add_member(H.ADMIN, org["id"], H.VIEWER.name)
        with self.assertRaises(PermissionDenied):
            ext.create_recommendation(
                H.VIEWER, org["id"], network["id"], "Nope", "manual_review")
        denied = [e for e in store.audit.entries()
                  if e["action"] == "ext_recommendation_create:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")

    def test_outsider_denied(self):
        ext, store, org, network, device = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_recommendation(
                H.OUTSIDER, org["id"], network["id"], "Nope", "manual_review")
        with self.assertRaises(PermissionDenied):
            ext.list_recommendations(H.OUTSIDER, org["id"])

    def test_extension_summary_counts(self):
        ext, store, org, network, device = make_extensions()
        ext.create_recommendation(H.MEMBER, org["id"], network["id"],
                                  "R", "telemetry_review")
        profile = ext.create_model_profile(
            H.MEMBER, org["id"], network["id"], "M", "other")
        ext.record_model_observation(H.MEMBER, org["id"], profile["id"], "x")
        change, push = make_push(ext, store, org, network, device)
        ext.record_push_outcome(H.MEMBER, push["id"], "reported_applied")
        firmware = ext.create_firmware(H.MEMBER, org["id"], "switching", "v1")
        ext.assign_firmware(H.MEMBER, org["id"], firmware["id"], device["id"])
        ext.create_traffic_policy(H.MEMBER, org["id"], network["id"], "P",
                                  TestTrafficPolicies.RULES)
        automation = H.make_automation(store, org)
        ext.record_automation_run(H.MEMBER, org["id"], automation["id"],
                                  "reported_completed")
        ext.create_page_config(H.MEMBER, org["id"], "PAGE-1", "One", [])
        ext.create_provisioning_reference(H.MEMBER, org["id"], network["id"],
                                          "DEV-NEW-1")
        collection = ext.create_collection_reference(
            H.MEMBER, org["id"], device["id"], "throughput", "5m")
        ext.record_collection_receipt(H.MEMBER, org["id"], collection["id"],
                                      3, "w")
        alert = H.make_alert(store, org)
        ext.record_alert_evaluation(H.MEMBER, org["id"], alert["id"], "ok")
        ext.record_alert_delivery(H.MEMBER, org["id"], alert["id"], "sms",
                                  "reported_queued")
        ext.create_connector_reference(H.MEMBER, org["id"], "C", "SYS-1")
        summary = ext.extension_summary(H.MEMBER, org["id"])
        self.assertEqual(summary, {
            "org_id": org["id"],
            "recommendations": 1,
            "model_profiles": 1,
            "model_observations": 1,
            "config_pushes": 1,
            "push_outcomes": 1,
            "firmware_records": 1,
            "firmware_assignments": 1,
            "traffic_policies": 1,
            "automation_runs": 1,
            "page_configs": 1,
            "provisioning_references": 1,
            "collection_references": 1,
            "collection_receipts": 1,
            "alert_evaluations": 1,
            "alert_deliveries": 1,
            "connector_references": 1,
        })

    def test_no_forbidden_key_on_extension_views(self):
        ext, store, org, network, device = make_extensions()
        recommendation = ext.create_recommendation(
            H.MEMBER, org["id"], network["id"], "R", "manual_review")
        profile = ext.create_model_profile(
            H.MEMBER, org["id"], network["id"], "M", "classification")
        observation = ext.record_model_observation(
            H.MEMBER, org["id"], profile["id"], "label")
        change, push = make_push(ext, store, org, network, device)
        outcome = ext.record_push_outcome(
            H.MEMBER, push["id"], "reported_failed")
        firmware = ext.create_firmware(H.MEMBER, org["id"], "switching", "v1")
        assignment = ext.assign_firmware(
            H.MEMBER, org["id"], firmware["id"], device["id"])
        policy = ext.create_traffic_policy(
            H.MEMBER, org["id"], network["id"], "P", TestTrafficPolicies.RULES)
        automation = H.make_automation(store, org)
        run = ext.record_automation_run(
            H.MEMBER, org["id"], automation["id"], "reported_completed")
        page = ext.create_page_config(
            H.MEMBER, org["id"], "PAGE-1", "One", TestPageConfigs.WIDGETS)
        provisioning = ext.create_provisioning_reference(
            H.MEMBER, org["id"], network["id"], "DEV-NEW-1")
        collection = ext.create_collection_reference(
            H.MEMBER, org["id"], device["id"], "throughput", "5m")
        receipt = ext.record_collection_receipt(
            H.MEMBER, org["id"], collection["id"], 1, "w")
        alert = H.make_alert(store, org)
        evaluation = ext.record_alert_evaluation(
            H.MEMBER, org["id"], alert["id"], "ok")
        delivery = ext.record_alert_delivery(
            H.MEMBER, org["id"], alert["id"], "push", "reported_failed")
        connector = ext.create_connector_reference(
            H.MEMBER, org["id"], "C", "SYS-1")
        views = [
            recommendation, profile, observation, push, outcome, firmware,
            assignment, policy, run, page, provisioning, collection, receipt,
            evaluation, delivery, connector,
            ext.get_model_profile(H.MEMBER, profile["id"]),
            ext.get_config_push(H.MEMBER, push["id"]),
            ext.get_assignment(H.MEMBER, assignment["id"]),
            ext.get_traffic_policy(H.MEMBER, policy["id"]),
            ext.get_page_config(H.MEMBER, page["id"]),
            ext.get_provisioning_reference(H.MEMBER, provisioning["id"]),
            ext.extension_summary(H.MEMBER, org["id"]),
        ]
        for view in views:
            for key in _all_keys(view):
                lowered = key.lower()
                for forbidden in FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(forbidden, lowered,
                                     "%s in key %r of %r"
                                     % (forbidden, key, view))


class MutantNetmgmtExtensions(NetmgmtExtensions):
    """The negative control's mutant: push state derives from the
    EARLIEST recorded outcome instead of the latest."""

    def _derive_push_state(self, outcomes):
        if not outcomes:
            return "recorded"
        return outcomes[0]["reported_state"]


def _push_scenario(ext_class):
    store, org = H.make_store()
    network, device = H.make_estate(store, org)
    ext = ext_class(store)
    change = H.make_change(store, org, network, device_id=device["id"])
    push = ext.create_config_push(H.MEMBER, org["id"], change["id"])
    ext.record_push_outcome(H.MEMBER, push["id"], "reported_failed")
    ext.record_push_outcome(H.MEMBER, push["id"], "reported_applied")
    return ext, push


class TestPushStateNegativeControl(unittest.TestCase):
    """Fresh negative control: the config-push current-state
    derivation (latest recorded outcome wins) must be load-bearing."""

    def test_canonical_expectation(self):
        """Canonical: with outcomes failed-then-applied recorded in
        that order, the push's current state is the LATEST outcome,
        reported_applied; a push with no outcomes reads recorded."""
        ext, push = _push_scenario(NetmgmtExtensions)
        view = ext.get_config_push(H.MEMBER, push["id"])
        self.assertEqual(view["current_state"], "reported_applied")
        store, org = H.make_store()
        network, device = H.make_estate(store, org)
        bare = NetmgmtExtensions(store)
        change = H.make_change(store, org, network)
        bare_push = bare.create_config_push(H.MEMBER, org["id"], change["id"])
        self.assertEqual(
            bare.get_config_push(H.MEMBER, bare_push["id"])["current_state"],
            "recorded")

    def test_implementation_matches_canonical(self):
        """Implementation: the list view derives the same state."""
        ext, push = _push_scenario(NetmgmtExtensions)
        views = ext.list_config_pushes(H.MEMBER, push["org_id"])
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]["current_state"], "reported_applied")
        self.assertEqual(views[0]["outcome_count"], 2)

    def test_mutant_would_not_derive(self):
        """Mutant: deriving from the earliest outcome reports
        reported_failed for the same records, so the canonical
        expectation applied to the mutant's output fails
        (asserted literally)."""
        ext, push = _push_scenario(MutantNetmgmtExtensions)
        view = ext.get_config_push(H.MEMBER, push["id"])
        self.assertEqual(view["current_state"], "reported_failed")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_applied")


if __name__ == "__main__":
    unittest.main()
