"""Final GAPS batch tests, second unit, for Collaboration L2
(GAPS.md section "Remainder Addition — Collaboration L2
(+3 forks)", inventory idx 595-599).

Pins the extension surface in ``collab/extensions_addition.py``:
innovation campaigns, ideas, idea states, endorsements, and
plan links with the idea's current state derived at read
(idx 595); the administration console's service, configuration
revision, and action records with current settings derived at
read and console writes gated on the core ``admin`` action
(idx 596); and the three labeled reference surfaces -- visitation
visits bound to core calendar events, rule definitions that
never execute, and device-connection records (idx 597), hardware
endpoint registrations and reported statuses (idx 598), and
connector definitions and exchange records that hold no content
and transmit nothing (idx 599).

Fresh negative control: ``TestNegativeControlIdeaDerivation``
three-legs the idea current-state derivation
(``_current_idea_label``) -- the canonical latest-label reading
holds (and opens the plan-link gate), the earliest-label mutant
does not produce it, and the mutant's outcome treated as the
expectation fails. See tests/README.md for the live drill
record.
"""

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from collab.errors import (  # noqa: E402
    NotFoundError, PermissionDenied, ValidationError,
)
from collab.extensions_addition import CollabExtensionsAddition  # noqa: E402
from collab_helpers import (  # noqa: E402
    ADMIN, MEMBER, OUTSIDER, VIEWER,
    create_sample_board, create_sample_event, make_store,
    share_sample_file,
)

CAMPAIGN_KEYS = {
    "id", "workspace_id", "campaign_ref", "title",
    "created_by", "created_utc",
}
IDEA_KEYS = {
    "id", "workspace_id", "campaign_id", "idea_ref", "title",
    "created_by", "created_utc",
}
IDEA_STATE_KEYS = {
    "id", "workspace_id", "campaign_id", "idea_id", "state_label",
    "created_by", "created_utc",
}
ENDORSEMENT_KEYS = {
    "id", "workspace_id", "campaign_id", "idea_id", "supporter_ref",
    "created_by", "created_utc",
}
PLAN_LINK_KEYS = {
    "id", "workspace_id", "campaign_id", "idea_id", "board_id",
    "generated_here", "created_by", "created_utc",
}
SERVICE_KEYS = {
    "id", "workspace_id", "service_ref", "service_label",
    "created_by", "created_utc",
}
REVISION_KEYS = {
    "id", "workspace_id", "service_id", "settings", "applied_here",
    "created_by", "created_utc",
}
ADMIN_ACTION_KEYS = {
    "id", "workspace_id", "service_id", "action_ref", "action_label",
    "target_ref", "outcome_label", "effected_here",
    "created_by", "created_utc",
}
VISIT_KEYS = {
    "id", "workspace_id", "visit_ref", "event_id", "visitor_ref",
    "participant_ref", "reference_stub", "reference_transport",
    "conducted_here", "media_here", "created_by", "created_utc",
}
VISIT_OUTCOME_KEYS = {
    "id", "workspace_id", "visit_id", "outcome_label",
    "reference_stub", "created_by", "created_utc",
}
RULE_KEYS = {
    "id", "workspace_id", "rule_ref", "rule_kind", "steps", "state",
    "reference_stub", "executed_here", "created_by", "created_utc",
}
CONNECTION_KEYS = {
    "id", "workspace_id", "device_ref", "visit_id", "outcome_label",
    "reference_stub", "reference_transport", "connected_here",
    "provisioned_here", "created_by", "created_utc",
}
ENDPOINT_KEYS = {
    "id", "workspace_id", "device_ref", "kind", "reference_stub",
    "manufactured_here", "connected_here", "created_by", "created_utc",
}
ENDPOINT_STATUS_KEYS = {
    "id", "workspace_id", "endpoint_id", "status_label",
    "reference_stub", "created_by", "created_utc",
}
CONNECTOR_KEYS = {
    "id", "workspace_id", "connector_ref", "product_label", "state",
    "reference_stub", "reference_transport", "connected_here",
    "created_by", "created_utc",
}
EXCHANGE_KEYS = {
    "id", "workspace_id", "connector_id", "direction", "object_ref",
    "file_id", "outcome_label", "reference_stub",
    "reference_transport", "transmitted_here", "content_held",
    "created_by", "created_utc",
}
FORBIDDEN_KEY_PARTS = ("score", "grade", "rating", "percent", "rank")


def assert_no_score_keys(case, obj, path="$"):
    """Recursively assert no score-shaped key exists anywhere."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "score-shaped key %r under %s" % (key, path))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


def make_ext():
    """Fresh store + canonical workspace + the addition surface."""
    store, workspace_id = make_store()
    return store, workspace_id, CollabExtensionsAddition(store)


def make_campaign(ext, workspace_id, ref="CAMP-1", actor=MEMBER):
    return ext.create_campaign(actor, workspace_id, ref,
                               "Improve onboarding")


def make_idea(ext, workspace_id, campaign_id, ref="IDEA-1",
              actor=MEMBER):
    return ext.submit_idea(actor, workspace_id, campaign_id, ref,
                           "One inbox for every request")


def adopt(ext, workspace_id, idea_id, actor=MEMBER):
    ext.record_idea_state(actor, workspace_id, idea_id,
                          "reported_submitted")
    ext.record_idea_state(actor, workspace_id, idea_id,
                          "reported_adopted")


class TestCampaigns(unittest.TestCase):
    """Idx 595: campaign records over core workspaces."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()

    def test_campaign_shape(self):
        campaign = make_campaign(self.ext, self.ws)
        self.assertEqual(set(campaign), CAMPAIGN_KEYS)
        self.assertEqual(campaign["id"], "inc-1")
        self.assertEqual(campaign["campaign_ref"], "CAMP-1")
        self.assertEqual(
            self.ext.get_campaign(MEMBER, self.ws, campaign["id"]),
            campaign)
        self.assertEqual(
            [c["id"] for c in self.ext.list_campaigns(MEMBER, self.ws)],
            ["inc-1"])

    def test_duplicate_campaign_ref_refused_and_no_id_consumed(self):
        make_campaign(self.ext, self.ws)
        with self.assertRaises(ValidationError):
            make_campaign(self.ext, self.ws)
        second = self.ext.create_campaign(
            MEMBER, self.ws, "CAMP-2", "Second drive")
        self.assertEqual(second["id"], "inc-2")

    def test_campaign_scoped_to_its_workspace(self):
        campaign = make_campaign(self.ext, self.ws)
        other = self.store.create_workspace("other-room", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_campaign(MEMBER, other["id"], campaign["id"])


class TestIdeasAndStates(unittest.TestCase):
    """Idx 595: ideas and their derived current state."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()
        self.campaign = make_campaign(self.ext, self.ws)

    def test_idea_shape_and_default_state(self):
        idea = make_idea(self.ext, self.ws, self.campaign["id"])
        self.assertEqual(set(idea), IDEA_KEYS)
        self.assertNotIn("current_state", idea)
        view = self.ext.idea_view(MEMBER, self.ws, idea["id"])
        self.assertEqual(view["current_state"], "reported_submitted")
        self.assertEqual(view["endorsement_count"], 0)
        self.assertEqual(view["plan_link_count"], 0)
        self.assertTrue(view["derived"])

    def test_duplicate_idea_ref_refused_within_campaign(self):
        make_idea(self.ext, self.ws, self.campaign["id"])
        with self.assertRaises(ValidationError):
            make_idea(self.ext, self.ws, self.campaign["id"])
        other = self.ext.create_campaign(
            MEMBER, self.ws, "CAMP-2", "Second drive")
        twin = make_idea(self.ext, self.ws, other["id"])
        self.assertEqual(twin["idea_ref"], "IDEA-1")

    def test_idea_into_unknown_campaign_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.submit_idea(MEMBER, self.ws, "inc-99", "IDEA-9",
                                 "Nowhere")

    def test_current_state_derives_latest_label(self):
        idea = make_idea(self.ext, self.ws, self.campaign["id"])
        state = self.ext.record_idea_state(
            MEMBER, self.ws, idea["id"], "reported_submitted")
        self.assertEqual(set(state), IDEA_STATE_KEYS)
        self.ext.record_idea_state(
            MEMBER, self.ws, idea["id"], "reported_under_review")
        self.ext.record_idea_state(
            MEMBER, self.ws, idea["id"], "reported_adopted")
        view = self.ext.idea_view(MEMBER, self.ws, idea["id"])
        self.assertEqual(view["current_state"], "reported_adopted")
        stored = self.ext.get_idea(MEMBER, self.ws, idea["id"])
        self.assertNotIn("current_state", stored)
        labels = [s["state_label"] for s in self.ext.list_idea_states(
            MEMBER, self.ws, idea["id"])]
        self.assertEqual(labels, ["reported_submitted",
                                  "reported_under_review",
                                  "reported_adopted"])

    def test_unknown_state_label_rejected(self):
        idea = make_idea(self.ext, self.ws, self.campaign["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_idea_state(
                MEMBER, self.ws, idea["id"], "shipped")


class TestEndorsements(unittest.TestCase):
    """Idx 595: crowd endorsement records."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()
        self.campaign = make_campaign(self.ext, self.ws)
        self.idea = make_idea(self.ext, self.ws, self.campaign["id"])

    def test_endorsement_shape_and_counts(self):
        endorsement = self.ext.record_endorsement(
            MEMBER, self.ws, self.idea["id"], "stakeholder-7")
        self.assertEqual(set(endorsement), ENDORSEMENT_KEYS)
        self.ext.record_endorsement(
            MEMBER, self.ws, self.idea["id"], "stakeholder-8")
        view = self.ext.idea_view(MEMBER, self.ws, self.idea["id"])
        self.assertEqual(view["endorsement_count"], 2)
        self.assertEqual(
            len(self.ext.list_endorsements(
                MEMBER, self.ws, self.idea["id"])), 2)

    def test_duplicate_supporter_refused(self):
        self.ext.record_endorsement(
            MEMBER, self.ws, self.idea["id"], "stakeholder-7")
        with self.assertRaises(ValidationError):
            self.ext.record_endorsement(
                MEMBER, self.ws, self.idea["id"], "stakeholder-7")


class TestPlanLinks(unittest.TestCase):
    """Idx 595: transformation of adopted ideas into plan links."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()
        self.campaign = make_campaign(self.ext, self.ws)
        self.idea = make_idea(self.ext, self.ws, self.campaign["id"])
        self.board = create_sample_board(self.store, self.ws)

    def test_link_refused_before_adoption(self):
        with self.assertRaises(ValidationError):
            self.ext.link_idea_to_plan(
                MEMBER, self.ws, self.idea["id"], self.board["id"])
        self.ext.record_idea_state(
            MEMBER, self.ws, self.idea["id"], "reported_under_review")
        with self.assertRaises(ValidationError):
            self.ext.link_idea_to_plan(
                MEMBER, self.ws, self.idea["id"], self.board["id"])

    def test_link_after_adoption_and_core_board_untouched(self):
        before = copy.deepcopy(
            self.store.list_boards(self.ws, MEMBER))
        adopt(self.ext, self.ws, self.idea["id"])
        link = self.ext.link_idea_to_plan(
            MEMBER, self.ws, self.idea["id"], self.board["id"])
        self.assertEqual(set(link), PLAN_LINK_KEYS)
        self.assertEqual(link["id"], "pln-1")
        self.assertFalse(link["generated_here"])
        after = self.store.list_boards(self.ws, MEMBER)
        self.assertEqual(before, after)
        view = self.ext.idea_view(MEMBER, self.ws, self.idea["id"])
        self.assertEqual(view["plan_link_count"], 1)

    def test_duplicate_link_and_unknown_board_refused(self):
        adopt(self.ext, self.ws, self.idea["id"])
        self.ext.link_idea_to_plan(
            MEMBER, self.ws, self.idea["id"], self.board["id"])
        with self.assertRaises(ValidationError):
            self.ext.link_idea_to_plan(
                MEMBER, self.ws, self.idea["id"], self.board["id"])
        with self.assertRaises(NotFoundError):
            self.ext.link_idea_to_plan(
                MEMBER, self.ws, self.idea["id"], "bd-99")

    def test_campaign_view_aggregates_derived_states(self):
        second = make_idea(self.ext, self.ws, self.campaign["id"],
                           ref="IDEA-2")
        adopt(self.ext, self.ws, self.idea["id"])
        self.ext.record_endorsement(
            MEMBER, self.ws, self.idea["id"], "stakeholder-7")
        self.ext.link_idea_to_plan(
            MEMBER, self.ws, self.idea["id"], self.board["id"])
        view = self.ext.campaign_view(
            MEMBER, self.ws, self.campaign["id"])
        self.assertEqual(view["idea_count"], 2)
        self.assertEqual(
            view["ideas_by_state"]["reported_adopted"], 1)
        self.assertEqual(
            view["ideas_by_state"]["reported_submitted"], 1)
        self.assertEqual(view["endorsement_count"], 1)
        self.assertEqual(view["plan_link_count"], 1)
        self.assertTrue(view["derived"])
        self.assertEqual(second["campaign_id"], self.campaign["id"])


class TestAdminConsole(unittest.TestCase):
    """Idx 596: administered services, configuration revisions,
    administrative actions; console writes are admin-gated."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()

    def make_service(self, ref="SVC-MSG"):
        return self.ext.register_admin_service(
            ADMIN, self.ws, ref, "Messaging service")

    def test_service_shape_and_no_settings_on_stored_record(self):
        service = self.make_service()
        self.assertEqual(set(service), SERVICE_KEYS)
        self.assertEqual(service["id"], "svc-1")
        self.assertNotIn("settings", service)
        view = self.ext.service_view(ADMIN, self.ws, service["id"])
        self.assertEqual(view["current_settings"], {})
        self.assertEqual(view["revision_count"], 0)

    def test_console_writes_require_the_admin_action(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_admin_service(
                MEMBER, self.ws, "SVC-MSG", "Messaging service")
        with self.assertRaises(PermissionDenied):
            self.ext.register_admin_service(
                VIEWER, self.ws, "SVC-MSG", "Messaging service")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_admin_service_register:denied", actions)
        service = self.make_service()
        self.assertEqual(service["id"], "svc-1")

    def test_duplicate_service_ref_refused(self):
        self.make_service()
        with self.assertRaises(ValidationError):
            self.make_service()

    def test_current_settings_derived_from_latest_revision(self):
        service = self.make_service()
        revision = self.ext.record_configuration_revision(
            ADMIN, self.ws, service["id"],
            {"external_sharing": "off", "retention": "p90d"})
        self.assertEqual(set(revision), REVISION_KEYS)
        self.assertFalse(revision["applied_here"])
        self.ext.record_configuration_revision(
            ADMIN, self.ws, service["id"],
            {"external_sharing": "on", "retention": "p90d"})
        view = self.ext.service_view(ADMIN, self.ws, service["id"])
        self.assertEqual(view["current_settings"],
                         {"external_sharing": "on",
                          "retention": "p90d"})
        self.assertEqual(view["revision_count"], 2)
        stored = self.ext.get_admin_service(
            ADMIN, self.ws, service["id"])
        self.assertNotIn("settings", stored)
        self.assertNotIn("current_settings", stored)

    def test_revision_settings_validation(self):
        service = self.make_service()
        for bad in (["not-a-dict"], {"nested": {"x": "y"}},
                    {"limit": 5}, {"": "blank-key"}):
            with self.assertRaises(ValidationError):
                self.ext.record_configuration_revision(
                    ADMIN, self.ws, service["id"], bad)
        self.assertEqual(
            self.ext.list_configuration_revisions(
                ADMIN, self.ws, service["id"]), [])

    def test_admin_action_records_and_console_view(self):
        service = self.make_service()
        self.ext.record_configuration_revision(
            ADMIN, self.ws, service["id"], {"a": "b"})
        action = self.ext.record_admin_action(
            ADMIN, self.ws, "ACT-1", "Disable external sharing",
            "workspace-policy", "reported_applied",
            service_id=service["id"])
        self.assertEqual(set(action), ADMIN_ACTION_KEYS)
        self.assertFalse(action["effected_here"])
        self.ext.record_admin_action(
            ADMIN, self.ws, "ACT-2", "Reset guest access",
            "guest-policy", "reported_refused")
        view = self.ext.console_view(ADMIN, self.ws)
        self.assertEqual(view["service_count"], 1)
        self.assertEqual(view["revision_count"], 1)
        self.assertEqual(view["action_count"], 2)
        self.assertEqual(view["latest_action_label"],
                         "Reset guest access")
        self.assertTrue(view["derived"])
        with self.assertRaises(ValidationError):
            self.ext.record_admin_action(
                ADMIN, self.ws, "ACT-3", "Anything", "target",
                "applied")
        with self.assertRaises(NotFoundError):
            self.ext.record_admin_action(
                ADMIN, self.ws, "ACT-4", "Anything", "target",
                "reported_applied", service_id="svc-99")


class TestVisitationReference(unittest.TestCase):
    """Idx 597: visit records, rule definitions, device
    connections -- labeled reference throughout."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()
        self.event = create_sample_event(self.store, self.ws)

    def make_visit(self):
        return self.ext.record_visit(
            MEMBER, self.ws, "VISIT-1", self.event["id"],
            "visitor-3", "resident-9")

    def test_visit_shape_and_stub_labels(self):
        visit = self.make_visit()
        self.assertEqual(set(visit), VISIT_KEYS)
        self.assertTrue(visit["reference_stub"])
        self.assertTrue(visit["reference_transport"])
        self.assertFalse(visit["conducted_here"])
        self.assertFalse(visit["media_here"])
        self.assertEqual(visit["event_id"], self.event["id"])

    def test_visit_requires_a_core_event(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_visit(
                MEMBER, self.ws, "VISIT-1", "evt-99",
                "visitor-3", "resident-9")
        visit = self.make_visit()
        self.assertEqual(visit["id"], "vst-1")
        with self.assertRaises(ValidationError):
            self.make_visit()

    def test_visit_outcomes_and_view(self):
        visit = self.make_visit()
        outcome = self.ext.record_visit_outcome(
            MEMBER, self.ws, visit["id"], "reported_completed")
        self.assertEqual(set(outcome), VISIT_OUTCOME_KEYS)
        self.assertTrue(outcome["reference_stub"])
        view = self.ext.visit_view(MEMBER, self.ws, visit["id"])
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome"], "reported_completed")
        with self.assertRaises(ValidationError):
            self.ext.record_visit_outcome(
                MEMBER, self.ws, visit["id"], "completed")

    def test_rule_definitions_never_execute(self):
        before = copy.deepcopy(
            self.store.list_events(self.ws, MEMBER))
        rule = self.ext.register_visitation_rule(
            MEMBER, self.ws, "RULE-1", "business_rule",
            ["verify visitor identity", "limit to 30 minutes"])
        self.assertEqual(set(rule), RULE_KEYS)
        self.assertTrue(rule["reference_stub"])
        self.assertFalse(rule["executed_here"])
        self.assertEqual(rule["state"], "recorded_reference_only")
        after = self.store.list_events(self.ws, MEMBER)
        self.assertEqual(before, after)
        with self.assertRaises(ValidationError):
            self.ext.register_visitation_rule(
                MEMBER, self.ws, "RULE-2", "guardrail", ["x"])
        with self.assertRaises(ValidationError):
            self.ext.register_visitation_rule(
                MEMBER, self.ws, "RULE-3", "workflow", [])

    def test_device_connection_records(self):
        visit = self.make_visit()
        connection = self.ext.record_device_connection(
            MEMBER, self.ws, "room-device-4", "reported_connected",
            visit_id=visit["id"])
        self.assertEqual(set(connection), CONNECTION_KEYS)
        self.assertTrue(connection["reference_stub"])
        self.assertTrue(connection["reference_transport"])
        self.assertFalse(connection["connected_here"])
        self.assertFalse(connection["provisioned_here"])
        self.assertEqual(
            len(self.ext.list_device_connections(
                MEMBER, self.ws, visit_id=visit["id"])), 1)
        with self.assertRaises(NotFoundError):
            self.ext.record_device_connection(
                MEMBER, self.ws, "room-device-5",
                "reported_connected", visit_id="vst-99")


class TestEndpointsReference(unittest.TestCase):
    """Idx 598: endpoint registrations and reported statuses."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()

    def test_endpoint_shape_and_stub_labels(self):
        endpoint = self.ext.register_endpoint(
            MEMBER, self.ws, "room-kit-1", "room_system")
        self.assertEqual(set(endpoint), ENDPOINT_KEYS)
        self.assertTrue(endpoint["reference_stub"])
        self.assertFalse(endpoint["manufactured_here"])
        self.assertFalse(endpoint["connected_here"])
        with self.assertRaises(ValidationError):
            self.ext.register_endpoint(
                MEMBER, self.ws, "holo-1", "hologram")

    def test_current_status_derived_from_latest_report(self):
        endpoint = self.ext.register_endpoint(
            MEMBER, self.ws, "desk-1", "desk_device")
        view = self.ext.endpoint_view(MEMBER, self.ws,
                                      endpoint["id"])
        self.assertIsNone(view["current_status"])
        status = self.ext.record_endpoint_status(
            MEMBER, self.ws, endpoint["id"], "reported_provisioning")
        self.assertEqual(set(status), ENDPOINT_STATUS_KEYS)
        self.ext.record_endpoint_status(
            MEMBER, self.ws, endpoint["id"], "reported_online")
        view = self.ext.endpoint_view(MEMBER, self.ws,
                                      endpoint["id"])
        self.assertEqual(view["current_status"], "reported_online")
        self.assertEqual(view["status_count"], 2)
        stored = self.ext.get_endpoint(MEMBER, self.ws,
                                       endpoint["id"])
        self.assertNotIn("current_status", stored)
        with self.assertRaises(ValidationError):
            self.ext.record_endpoint_status(
                MEMBER, self.ws, endpoint["id"], "online")


class TestConnectorsReference(unittest.TestCase):
    """Idx 599: connector definitions and exchange records."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()

    def make_connector(self):
        return self.ext.register_connector(
            MEMBER, self.ws, "CONN-OFFICE", "Office suite")

    def test_connector_shape_and_stub_labels(self):
        connector = self.make_connector()
        self.assertEqual(set(connector), CONNECTOR_KEYS)
        self.assertTrue(connector["reference_stub"])
        self.assertTrue(connector["reference_transport"])
        self.assertFalse(connector["connected_here"])
        self.assertEqual(connector["state"],
                         "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.make_connector()

    def test_exchange_records_hold_no_content(self):
        connector = self.make_connector()
        shared = share_sample_file(self.store, self.ws)
        exchange = self.ext.record_exchange(
            MEMBER, self.ws, connector["id"], "outbound",
            "external-doc-11", "reported_delivered",
            file_id=shared["id"])
        self.assertEqual(set(exchange), EXCHANGE_KEYS)
        self.assertTrue(exchange["reference_stub"])
        self.assertTrue(exchange["reference_transport"])
        self.assertFalse(exchange["transmitted_here"])
        self.assertFalse(exchange["content_held"])
        self.assertNotIn("content", exchange)
        stored_file = self.store.get_file(
            self.ws, shared["id"], MEMBER)
        self.assertEqual(stored_file["version"], 1)

    def test_exchange_validation(self):
        connector = self.make_connector()
        with self.assertRaises(NotFoundError):
            self.ext.record_exchange(
                MEMBER, self.ws, connector["id"], "outbound",
                "external-doc-11", "reported_delivered",
                file_id="file-99")
        with self.assertRaises(ValidationError):
            self.ext.record_exchange(
                MEMBER, self.ws, connector["id"], "sideways",
                "external-doc-11", "reported_delivered")
        with self.assertRaises(ValidationError):
            self.ext.record_exchange(
                MEMBER, self.ws, connector["id"], "inbound",
                "external-doc-11", "delivered")

    def test_connector_view_counts_by_outcome(self):
        connector = self.make_connector()
        self.ext.record_exchange(
            MEMBER, self.ws, connector["id"], "outbound",
            "doc-1", "reported_delivered")
        self.ext.record_exchange(
            MEMBER, self.ws, connector["id"], "inbound",
            "doc-2", "reported_queued")
        self.ext.record_exchange(
            MEMBER, self.ws, connector["id"], "outbound",
            "doc-3", "reported_delivered")
        view = self.ext.connector_view(
            MEMBER, self.ws, connector["id"])
        self.assertEqual(view["exchange_count"], 3)
        self.assertEqual(
            view["exchanges_by_outcome"]["reported_delivered"], 2)
        self.assertEqual(
            view["exchanges_by_outcome"]["reported_failed"], 0)
        self.assertTrue(view["derived"])


class TestAccessAndAudit(unittest.TestCase):
    """Access discipline across the whole addition surface."""

    def setUp(self):
        self.store, self.ws, self.ext = make_ext()

    def test_viewer_is_read_only_and_denial_is_audited(self):
        campaign = make_campaign(self.ext, self.ws)
        self.assertEqual(
            self.ext.get_campaign(VIEWER, self.ws,
                                  campaign["id"])["id"],
            campaign["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_campaign(
                VIEWER, self.ws, "CAMP-9", "Viewer drive")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_campaign_create:denied", actions)

    def test_outsider_denied_at_the_membership_boundary(self):
        campaign = make_campaign(self.ext, self.ws)
        with self.assertRaises(PermissionDenied):
            self.ext.get_campaign(OUTSIDER, self.ws, campaign["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_campaign(
                OUTSIDER, self.ws, "CAMP-9", "Outsider drive")

    def test_mutations_audited_with_exta_prefix(self):
        make_campaign(self.ext, self.ws)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_campaign_create", actions)


class TestNoScoreKeys(unittest.TestCase):
    """No score-shaped key exists anywhere on the new surface."""

    def test_views_and_records_carry_no_score_keys(self):
        store, ws, ext = make_ext()
        campaign = make_campaign(ext, ws)
        idea = make_idea(ext, ws, campaign["id"])
        adopt(ext, ws, idea["id"])
        board = create_sample_board(store, ws)
        ext.record_endorsement(MEMBER, ws, idea["id"],
                               "stakeholder-7")
        ext.link_idea_to_plan(MEMBER, ws, idea["id"], board["id"])
        service = ext.register_admin_service(
            ADMIN, ws, "SVC-MSG", "Messaging service")
        ext.record_configuration_revision(
            ADMIN, ws, service["id"], {"a": "b"})
        ext.record_admin_action(
            ADMIN, ws, "ACT-1", "Toggle", "target",
            "reported_applied", service_id=service["id"])
        event = create_sample_event(store, ws)
        visit = ext.record_visit(
            MEMBER, ws, "VISIT-1", event["id"], "visitor-3",
            "resident-9")
        endpoint = ext.register_endpoint(
            MEMBER, ws, "room-kit-1", "room_system")
        connector = ext.register_connector(
            MEMBER, ws, "CONN-OFFICE", "Office suite")
        ext.record_exchange(
            MEMBER, ws, connector["id"], "outbound", "doc-1",
            "reported_delivered")
        for obj in (
                ext.campaign_view(MEMBER, ws, campaign["id"]),
                ext.idea_view(MEMBER, ws, idea["id"]),
                ext.service_view(ADMIN, ws, service["id"]),
                ext.console_view(ADMIN, ws),
                ext.visit_view(MEMBER, ws, visit["id"]),
                ext.endpoint_view(MEMBER, ws, endpoint["id"]),
                ext.connector_view(MEMBER, ws, connector["id"]),
                ext.list_campaigns(MEMBER, ws),
                ext.list_admin_actions(ADMIN, ws)):
            assert_no_score_keys(self, obj)


class _EarliestIdeaExtensions(CollabExtensionsAddition):
    """Mutant: the idea current-state seam reads the earliest
    recorded state label instead of the latest."""

    @staticmethod
    def _current_idea_label(states):
        return states[0]["state_label"] if states else None


class TestNegativeControlIdeaDerivation(unittest.TestCase):
    """Fresh negative control for the idea current-state
    derivation (``_current_idea_label``): an idea's current state
    is its LATEST recorded label, and the plan-link gate opens
    only on the derived ``reported_adopted`` state. The
    earliest-label mutant must misstate both."""

    def _flow(self, ext, store, workspace_id):
        campaign = make_campaign(ext, workspace_id)
        idea = make_idea(ext, workspace_id, campaign["id"])
        board = create_sample_board(store, workspace_id)
        adopt(ext, workspace_id, idea["id"])
        return campaign, idea, board

    def test_canonical_latest_label_wins(self):
        store, ws, ext = make_ext()
        campaign, idea, board = self._flow(ext, store, ws)
        view = ext.idea_view(MEMBER, ws, idea["id"])
        self.assertEqual(view["current_state"], "reported_adopted")
        link = ext.link_idea_to_plan(
            MEMBER, ws, idea["id"], board["id"])
        self.assertEqual(link["board_id"], board["id"])
        campaign_view = ext.campaign_view(MEMBER, ws,
                                          campaign["id"])
        self.assertEqual(
            campaign_view["ideas_by_state"]["reported_adopted"], 1)

    def test_mutant_reports_earliest_and_gate_stays_shut(self):
        store, ws, _ext = make_ext()
        mutant = _EarliestIdeaExtensions(store)
        _campaign, idea, board = self._flow(mutant, store, ws)
        view = mutant.idea_view(MEMBER, ws, idea["id"])
        self.assertEqual(view["current_state"],
                         "reported_submitted")
        with self.assertRaises(ValidationError):
            mutant.link_idea_to_plan(
                MEMBER, ws, idea["id"], board["id"])

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        store, ws, _ext = make_ext()
        mutant = _EarliestIdeaExtensions(store)
        _campaign, idea, _board = self._flow(mutant, store, ws)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.idea_view(MEMBER, ws,
                                 idea["id"])["current_state"],
                "reported_adopted")


if __name__ == "__main__":
    unittest.main()
