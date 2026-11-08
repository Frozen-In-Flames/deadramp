"""Final GAPS batch, second unit -- Communication L3 remainder addition.

Pins ``src/comm/extensions_addition.py`` for the 2 OPEN entries of
the "Remainder Addition -- Communication L3-adjacent (+1 fork)"
section (inventory idx 658-659): idx 658 closes ``reference``
(connector definitions + reported exchanges, labeled stub and
transport) and idx 659 closes ``built`` in records form
(persistent room records + memberships + activity, content never
held). Also pins derived-never-stored, RBAC with denied attempts
audited, the High apparatus (auditor denied every addition
operation; hash chain verifies), failed operations consuming no
ids, and the no-content discipline (content-shaped kwargs raise
``TypeError``; a signature scan and a recursive key scan pin the
absence). Fresh negative control on the seam ``_latest_label``.
"""

import inspect
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from comm import extensions_addition as exta_mod  # noqa: E402
from comm.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from comm.extensions_addition import CommExtensionsAddition  # noqa: E402
from comm_helpers import ADMIN, AUDITOR, OPERATOR, VIEWER, make_store  # noqa: E402

BANNED_KEYS = {"content", "body", "payload", "document", "transcript",
               "message_text", "text", "file", "attachment"}


def fresh_addition():
    store, contact, group, channel = make_store()
    return CommExtensionsAddition(store), store, contact


def scan_no_content(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert k not in BANNED_KEYS, "banned key %r at %s" % (k, path)
            scan_no_content(v, path + "." + str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            scan_no_content(v, "%s[%d]" % (path, i))


class TestConnectorReference(unittest.TestCase):
    """idx 658 -- app integration & connector platform (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_addition()

    def test_definition_shape_and_labels(self):
        rec = self.ext.record_connector_definition(
            "tool-ref-1", "Example Tool", "app_integration", OPERATOR)
        self.assertEqual(rec["id"], "acn-1")
        self.assertIs(rec["reference_stub"], True)
        self.assertIs(rec["reference_transport"], True)
        self.assertIs(rec["connected_here"], False)
        self.assertIs(rec["synced_here"], False)
        self.assertIs(rec["credentials_held"], False)
        self.assertIs(rec["sent_here"], False)
        self.assertIs(rec["transmitted_here"], False)

    def test_kind_validated_and_ref_unique(self):
        with self.assertRaises(ValidationError):
            self.ext.record_connector_definition("r", "x", "telepathy", OPERATOR)
        self.ext.record_connector_definition("tool-ref-1", "T", "api_connector", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_connector_definition("tool-ref-1", "T2", "api_connector", OPERATOR)
        rec = self.ext.record_connector_definition("tool-ref-2", "T2", "api_connector", OPERATOR)
        self.assertEqual(rec["id"], "acn-2")

    def test_exchange_and_view_derived(self):
        c = self.ext.record_connector_definition("tool-ref-1", "T", "data_sync", OPERATOR)
        view = self.ext.connector_view(c["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "unreported")
        self.assertEqual(view["total_records_reported"], 0)
        self.ext.record_connector_exchange(c["id"], "reported_partial", OPERATOR, records_reported=5)
        self.ext.record_connector_exchange(c["id"], "reported_completed", OPERATOR, records_reported=7)
        self.ext.record_connector_exchange(c["id"], "reported_completed", OPERATOR)
        view = self.ext.connector_view(c["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_completed")
        self.assertEqual(view["exchange_count"], 3)
        self.assertEqual(view["total_records_reported"], 12)
        self.assertEqual(view["exchanges_without_count"], 1)
        self.assertNotIn("current_outcome", view["definition"])
        ex = view["exchanges"][0]
        self.assertIs(ex["reference_stub"], True)
        self.assertIs(ex["imported_here"], False)
        self.assertIs(ex["transmitted_here"], False)

    def test_exchange_validation_and_unknown_connector(self):
        c = self.ext.record_connector_definition("tool-ref-1", "T", "data_sync", OPERATOR)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_connector_exchange(c["id"], "reported_x", OPERATOR, records_reported=bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_exchange("acn-99", "reported_x", OPERATOR)
        rec = self.ext.record_connector_exchange(c["id"], "reported_ok", OPERATOR)
        self.assertEqual(rec["id"], "aex-1")

    def test_content_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_connector_definition("r", "x", "api_connector", OPERATOR, payload={})
        c = self.ext.record_connector_definition("tool-ref-1", "T", "api_connector", OPERATOR)
        with self.assertRaises(TypeError):
            self.ext.record_connector_exchange(c["id"], "reported_x", OPERATOR, content="secret")


class TestWorkspaceRoomBuilt(unittest.TestCase):
    """idx 659 -- persistent channel / workspace surface (built, records)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_addition()

    def test_room_shape_distinct_from_delivery_channel(self):
        room = self.ext.create_workspace_room("room-general", "General", OPERATOR)
        self.assertEqual(room["id"], "wsr-1")
        self.assertIs(room["records_surface"], True)
        self.assertIs(room["content_held"], False)
        self.assertIs(room["real_time_transport_here"], False)
        self.assertIs(room["workspace_substrate_here"], False)
        # Distinct namespace from the core delivery channels.
        channels = self.store.list_channels(OPERATOR)
        self.assertTrue(all(ch["id"].startswith("ch-") for ch in channels))
        self.assertFalse(room["id"].startswith("ch-"))

    def test_room_ref_unique_and_no_id_on_failure(self):
        self.ext.create_workspace_room("room-general", "General", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.create_workspace_room("room-general", "Again", OPERATOR)
        room = self.ext.create_workspace_room("room-ops", "Ops", OPERATOR)
        self.assertEqual(room["id"], "wsr-2")

    def test_membership_binds_core_contact_and_dedupes(self):
        room = self.ext.create_workspace_room("room-general", "General", OPERATOR)
        m = self.ext.record_room_membership(room["id"], self.contact["id"], OPERATOR)
        self.assertEqual(m["id"], "wmb-1")
        self.assertEqual(m["contact_id"], self.contact["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_room_membership(room["id"], self.contact["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_room_membership(room["id"], "ct-99", OPERATOR)
        view = self.ext.workspace_room_view(room["id"], OPERATOR)
        self.assertEqual(view["member_count"], 1)
        self.assertEqual(view["member_contact_ids"], [self.contact["id"]])
        self.assertNotIn("member_count", view["room"])

    def test_activity_binds_core_message_by_id_only(self):
        room = self.ext.create_workspace_room("room-general", "General", OPERATOR)
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="Hello",
            contact_ids=[self.contact["id"]], channel_kinds=["email"])
        act = self.ext.record_room_activity(
            room["id"], "reported_message_posted", OPERATOR, message_id=msg["id"])
        self.assertEqual(act["message_id"], msg["id"])
        self.assertIs(act["content_held"], False)
        self.assertIs(act["sent_here"], False)
        # Recording activity dispatches nothing.
        deliveries = self.store.list_deliveries(msg["id"], OPERATOR)
        self.assertEqual(deliveries[0]["status"], "queued")
        with self.assertRaises(NotFoundError):
            self.ext.record_room_activity(room["id"], "x", OPERATOR, message_id="msg-99")

    def test_current_activity_derived_from_latest(self):
        room = self.ext.create_workspace_room("room-general", "General", OPERATOR)
        view = self.ext.workspace_room_view(room["id"], OPERATOR)
        self.assertEqual(view["current_activity"], "none_recorded")
        self.ext.record_room_activity(room["id"], "reported_thread_started", OPERATOR)
        self.ext.record_room_activity(room["id"], "reported_pinned", OPERATOR)
        view = self.ext.workspace_room_view(room["id"], OPERATOR)
        self.assertEqual(view["current_activity"], "reported_pinned")
        self.assertEqual(view["activity_count"], 2)
        self.assertNotIn("current_activity", view["room"])

    def test_content_kwargs_raise_type_error(self):
        room = self.ext.create_workspace_room("room-general", "General", OPERATOR)
        with self.assertRaises(TypeError):
            self.ext.record_room_activity(room["id"], "x", OPERATOR, body="hello")
        with self.assertRaises(TypeError):
            self.ext.create_workspace_room("r2", "x", OPERATOR, document="doc")


class TestAdditionDiscipline(unittest.TestCase):
    """Cross-cutting: RBAC, High apparatus, scans, summary."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_addition()

    def test_viewer_write_denied_and_audited(self):
        audit = self.store.audit
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.record_connector_definition("r", "x", "api_connector", VIEWER)
        entries = audit.entries()
        self.assertEqual(len(entries), before + 1)
        self.assertEqual(entries[-1]["action"], "exta_message_compose:denied")
        self.assertEqual(entries[-1]["actor"], "carol")

    def test_auditor_denied_every_addition_operation(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace_room("r", "x", AUDITOR)
        room = self.ext.create_workspace_room("r", "x", OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.ext.workspace_room_view(room["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.addition_report_summary(AUDITOR)
        # The auditor's core duty still works.
        ok, bad = self.store.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(bad)

    def test_mutations_audited_exta_prefix_and_chain_verifies(self):
        self.ext.record_connector_definition("r", "x", "api_connector", OPERATOR)
        self.ext.create_workspace_room("room-1", "R", OPERATOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_connector_definition_record", actions)
        self.assertIn("exta_workspace_room_create", actions)
        ok, bad = self.store.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(bad)

    def test_no_content_shaped_parameter_anywhere(self):
        banned = {"content", "body", "payload", "document", "transcript",
                  "audio", "key_material", "signature_bytes", "media"}
        for name, fn in inspect.getmembers(CommExtensionsAddition, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            params = set(inspect.signature(fn).parameters)
            self.assertEqual(params & banned, set(),
                             "%s accepts a content-shaped parameter" % name)

    def test_recursive_no_content_scan_over_surface(self):
        c = self.ext.record_connector_definition("tool-1", "T", "data_sync", OPERATOR)
        self.ext.record_connector_exchange(c["id"], "reported_completed", OPERATOR, records_reported=3)
        room = self.ext.create_workspace_room("room-1", "R", OPERATOR)
        self.ext.record_room_membership(room["id"], self.contact["id"], OPERATOR)
        self.ext.record_room_activity(room["id"], "reported_active", OPERATOR)
        for obj in (self.ext.connector_view(c["id"], OPERATOR),
                    self.ext.workspace_room_view(room["id"], OPERATOR),
                    self.ext.addition_report_summary(OPERATOR)):
            scan_no_content(obj)

    def test_report_summary_counts_track_records(self):
        s = self.ext.addition_report_summary(OPERATOR)
        self.assertEqual(s["method"], "deterministic_counts")
        self.assertEqual(s["workspace_rooms"], 0)
        self.ext.create_workspace_room("room-1", "R", OPERATOR)
        s = self.ext.addition_report_summary(OPERATOR)
        self.assertEqual(s["workspace_rooms"], 1)

    def test_no_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace_room("r", "x", None)


def _mutant_latest_label(records, key):
    if not records:
        return None
    return records[0][key]


class TestNegativeControlLatestLabelAddition(unittest.TestCase):
    """Fresh negative control: current label = LATEST record's label
    (seam ``_latest_label`` in ``comm.extensions_addition``)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_addition()
        self.room = self.ext.create_workspace_room("room-1", "R", OPERATOR)
        self.ext.record_room_activity(self.room["id"], "reported_open", OPERATOR)
        self.ext.record_room_activity(self.room["id"], "reported_archived", OPERATOR)

    def test_canonical_view_uses_latest_activity(self):
        view = self.ext.workspace_room_view(self.room["id"], OPERATOR)
        self.assertEqual(view["current_activity"], "reported_archived")

    def test_mutant_earliest_differs(self):
        records = [{"activity_label": "reported_open"},
                   {"activity_label": "reported_archived"}]
        self.assertEqual(exta_mod._latest_label(records, "activity_label"), "reported_archived")
        self.assertEqual(_mutant_latest_label(records, "activity_label"), "reported_open")

    def test_canonical_expectation_rejects_mutant(self):
        view = self.ext.workspace_room_view(self.room["id"], OPERATOR)
        mutant_value = _mutant_latest_label(view["activities"], "activity_label")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_activity"], mutant_value)


if __name__ == "__main__":
    unittest.main()
