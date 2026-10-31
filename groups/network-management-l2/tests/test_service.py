"""Core function 10: REST API -- live HTTP semantics (SI-10, AC-3)."""

import http.client
import json
import threading
import unittest
from urllib.parse import quote

import netmgmt_helpers as H
from netmgmt.audit import AuditLog
from netmgmt.service import make_server
from netmgmt.store import NetmgmtStore


class HttpFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store = NetmgmtStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(H.USERS_REGISTRY))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        conn.request(method, path,
                     body=json.dumps(body) if body is not None else None,
                     headers=headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}

    def make_org_and_network(self):
        status, org = self.call("POST", "/organizations", "bob", "member",
                                {"ref": "AGENCY-1", "label": "Agency One"})
        self.assertEqual(status, 201)
        status, _ = self.call("POST", "/organizations/%s/members" % org["id"],
                              "alice", "admin", {"username": "erin"})
        self.assertEqual(status, 200)
        status, network = self.call(
            "POST", "/organizations/%s/networks" % org["id"],
            "bob", "member",
            {"ref": "NET-HQ", "label": "HQ network",
             "site_ref": "SITE-HQ"})
        self.assertEqual(status, 201)
        return org, network


class TestService(HttpFixture):
    def test_health_needs_no_auth(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_are_401(self):
        status, _ = self.call("GET", "/organizations", user="mallory",
                              role="member")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations", user="bob",
                              role="admin")  # bob is registered as member
        self.assertEqual(status, 401)

    def test_full_flow_over_http(self):
        org, network = self.make_org_and_network()
        org_id = org["id"]
        status, device = self.call(
            "POST", "/organizations/%s/devices" % org_id, "bob", "member",
            {"network_id": network["id"], "ref": "DEV-SW-1",
             "device_class": "switching", "model_ref": "MODEL-SW-1"})
        self.assertEqual(status, 201)
        self.assertEqual(device["derived_status"], "unknown")
        status, record = self.call(
            "POST", "/devices/%s/telemetry" % device["id"], "bob", "member",
            {"metric": "throughput", "value": 100, "unit": "mbps",
             "recorded_utc": H.TELEMETRY_RECORDED_UTC})
        self.assertEqual(status, 201)
        status, view = self.call(
            "GET", "/devices/%s?as_of=%s" % (device["id"], quote(H.AS_OF_FRESH)),
            "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(view["derived_status"], "fresh")
        status, stale = self.call(
            "GET", "/devices/%s?as_of=%s" % (device["id"], quote(H.AS_OF_STALE)),
            "bob", "member")
        self.assertEqual(stale["derived_status"], "stale")
        status, change = self.call(
            "POST", "/organizations/%s/changes" % org_id, "bob", "member",
            {"network_id": network["id"], "change_kind": "update",
             "summary": "Tune HQ policy", "device_id": device["id"]})
        self.assertEqual(status, 201)
        # The requester cannot decide his own change: 403.
        status, _ = self.call("POST", "/changes/%s/decide" % change["id"],
                              "bob", "member", {"approve": True})
        self.assertEqual(status, 403)
        status, decided = self.call(
            "POST", "/changes/%s/decide" % change["id"], "erin", "member",
            {"approve": True})
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")
        device_before = dict(self.store._devices[device["id"]])
        status, closed = self.call("POST", "/changes/%s/close" % change["id"],
                                   "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(dict(self.store._devices[device["id"]]),
                         device_before)
        status, summary = self.call(
            "GET", "/organizations/%s/summary" % org_id, "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(summary["changes_by_status"]["closed"], 1)

    def test_viewer_is_read_only_over_http(self):
        org, network = self.make_org_and_network()
        status, _ = self.call(
            "POST", "/organizations/%s/devices" % org["id"],
            "carol", "viewer",
            {"network_id": network["id"], "ref": "DEV-1",
             "device_class": "other", "model_ref": "M"})
        self.assertEqual(status, 403)

    def test_validation_and_not_found(self):
        org, network = self.make_org_and_network()
        status, device = self.call(
            "POST", "/organizations/%s/devices" % org["id"], "bob", "member",
            {"network_id": network["id"], "ref": "DEV-SW-1",
             "device_class": "switching", "model_ref": "MODEL-SW-1"})
        self.assertEqual(status, 201)
        status, payload = self.call(
            "POST", "/devices/%s/telemetry" % device["id"], "bob", "member",
            {"metric": "throughput", "value": 1.5, "unit": "mbps",
             "recorded_utc": H.TELEMETRY_RECORDED_UTC})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        status, _ = self.call("GET", "/organizations/org-99", "bob", "member")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/nope", "bob", "member")
        self.assertEqual(status, 404)

    def test_automations_and_alerts_over_http(self):
        org, network = self.make_org_and_network()
        org_id = org["id"]
        status, automation = self.call(
            "POST", "/organizations/%s/automations" % org_id,
            "bob", "member",
            {"name": "Nightly review", "steps": ["collect", "review"]})
        self.assertEqual(status, 201)
        status, fetched = self.call(
            "GET", "/automations/%s" % automation["id"], "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["steps"], ["collect", "review"])
        status, alert = self.call(
            "POST", "/organizations/%s/alerts" % org_id, "bob", "member",
            {"kind": "general", "message": "Review HQ network",
             "network_id": network["id"]})
        self.assertEqual(status, 201)
        status, acked = self.call(
            "POST", "/alerts/%s/acknowledge" % alert["id"], "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(acked["acknowledged_by"], "bob")
        status, hits = self.call("GET", "/search?q=hq", "bob", "member")
        self.assertEqual(status, 200)
        self.assertEqual(len(hits["networks"]), 1)
        self.assertEqual(len(hits["alerts"]), 1)

    def test_audit_endpoint_admin_only_and_denials_audited(self):
        status, _ = self.call("GET", "/audit", "bob", "member")
        self.assertEqual(status, 403)
        status, payload = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in payload["entries"]]
        self.assertTrue(any(a.endswith(":denied") for a in actions))
        self.assertIn("audit_read", actions)


if __name__ == "__main__":
    unittest.main()
