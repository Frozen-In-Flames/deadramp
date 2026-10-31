"""Devices and control actions (core functions 5 and 6):
records only — recording a control action sends nothing and
changes nothing."""

import unittest

from media_helpers import (ADMIN, AT, OPERATOR, VIEWER, make_device,
                           make_endpoints, make_org, make_store)

from media.errors import NotFoundError, ValidationError


class DeviceTests(unittest.TestCase):
    def test_device_shape_and_unique_ref(self):
        store, _audit = make_store()
        org = make_org(store)
        source, _d = make_endpoints(store, org)
        device = make_device(store, org, endpoint=source)
        self.assertEqual(device["endpoint_id"], source["id"])
        self.assertEqual(
            set(device),
            {"id", "org_id", "ref", "label", "kind_label",
             "endpoint_id", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            make_device(store, org)

    def test_device_endpoint_must_share_the_org(self):
        store, _audit = make_store()
        org = make_org(store)
        other = store.create_organization(ADMIN, "ORG-0002", "Second")
        foreign, _fd = make_endpoints(store, other)
        with self.assertRaises(ValidationError):
            store.create_device(OPERATOR, org["id"], "ENC-9", "x",
                                endpoint_id=foreign["id"])
        with self.assertRaises(NotFoundError):
            store.create_device(OPERATOR, org["id"], "ENC-9", "x",
                                endpoint_id="end-99")


class ControlActionTests(unittest.TestCase):
    def test_control_action_record_shape(self):
        store, _audit = make_store()
        org = make_org(store)
        device = make_device(store, org)
        record = store.record_control_action(
            OPERATOR, device["id"], "start", note="begin contribution",
            at=AT)
        self.assertEqual(record["action"], "start")
        self.assertEqual(record["note"], "begin contribution")
        self.assertEqual(record["recorded_at"], AT)

    def test_recording_an_action_changes_nothing_else(self):
        """The registry describes control; it does not perform it.
        After a 'start' action is recorded, the device record is
        byte-identical, no session exists, and the route (if any)
        is untouched — the action is a fact in the log, not a
        signal."""
        store, _audit = make_store()
        org = make_org(store)
        device = make_device(store, org)
        before = store.get_device(ADMIN, device["id"])
        store.record_control_action(OPERATOR, device["id"], "start")
        store.record_control_action(OPERATOR, device["id"], "adjust",
                                    note="aim camera")
        self.assertEqual(store.get_device(ADMIN, device["id"]), before)
        self.assertEqual(store.list_sessions(ADMIN), [])
        self.assertEqual(store.summary(ADMIN)["control_actions"], 2)

    def test_action_vocabulary_and_filters(self):
        store, _audit = make_store()
        org = make_org(store)
        device = make_device(store, org)
        with self.assertRaises(ValidationError):
            store.record_control_action(OPERATOR, device["id"], "wipe")
        with self.assertRaises(NotFoundError):
            store.record_control_action(OPERATOR, "dev-99", "start")
        store.record_control_action(OPERATOR, device["id"], "stop")
        self.assertEqual(
            len(store.list_control_actions(VIEWER, action="stop")), 1)
        self.assertEqual(
            store.list_control_actions(VIEWER, action="restart"), [])


if __name__ == "__main__":
    unittest.main()
