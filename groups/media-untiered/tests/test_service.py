"""The REST API over real HTTP (core function 10): health is
public, auth is enforced, the session guard binds end to end,
denied attempts are audited."""

import http.client
import json
import threading
import unittest

from media.service import make_server

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=10)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers or {})
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}

    def _org_route(self, suffix):
        _s, org = self.call("POST", "/organizations", ALICE,
                            {"ref": "ORG-" + suffix,
                             "label": "Service office"})
        self.assertEqual(_s, 201)
        _s, src = self.call("POST", "/endpoints", BOB,
                            {"org_id": org["id"], "ref": "NET-" + suffix,
                             "label": "HQ", "kind": "agency_network"})
        self.assertEqual(_s, 201)
        _s, dst = self.call("POST", "/endpoints", BOB,
                            {"org_id": org["id"],
                             "ref": "CLOUD-" + suffix,
                             "label": "Cloud", "kind": "cloud_destination"})
        self.assertEqual(_s, 201)
        status, route = self.call(
            "POST", "/routes", BOB,
            {"org_id": org["id"], "label": "Contribution",
             "source_endpoint_id": src["id"],
             "destination_endpoint_id": dst["id"]})
        self.assertEqual(status, 201)
        return org, route

    def test_health_is_public(self):
        status, body = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_are_401(self):
        status, _b = self.call("GET", "/organizations",
                               {"X-User": "mallory", "X-Role": "admin"})
        self.assertEqual(status, 401)
        status, _b = self.call("GET", "/organizations",
                               {"X-User": "alice", "X-Role": "viewer"})
        self.assertEqual(status, 401)
        status, _b = self.call("GET", "/organizations")
        self.assertEqual(status, 401)

    def test_unknown_path_is_404_json(self):
        status, body = self.call("GET", "/nope", ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_full_flow_with_session_guard(self):
        org, route = self._org_route("FLOW")
        status, session = self.call(
            "POST", "/sessions", BOB,
            {"route_id": route["id"],
             "started_at": "2026-01-10T10:00:00+00:00"})
        self.assertEqual(status, 201)
        self.assertEqual(session["state"], "live")
        # The guard binds over HTTP too.
        status, body = self.call("POST", "/sessions", BOB,
                                 {"route_id": route["id"]})
        self.assertEqual(status, 400)
        self.assertIn("live session", body["error"])
        status, view = self.call("GET", "/routes/" + route["id"], CAROL)
        self.assertEqual(view["state"], "live")
        status, snap = self.call(
            "POST", "/snapshots", BOB,
            {"subject_kind": "route", "subject_id": route["id"],
             "status": "up"})
        self.assertEqual(status, 201)
        status, current = self.call(
            "GET",
            "/current-status?subject_kind=route&subject_id="
            + route["id"], CAROL)
        self.assertEqual(current["status"], "up")
        status, stopped = self.call(
            "POST", "/sessions/" + session["id"] + "/stop", BOB,
            {"stopped_at": "2026-01-10T11:00:00+00:00"})
        self.assertEqual(status, 200)
        self.assertEqual(stopped["state"], "ended")

    def test_viewer_write_is_403_and_audited(self):
        org, _route = self._org_route("DENY")
        status, _b = self.call("POST", "/endpoints", CAROL,
                               {"org_id": org["id"], "ref": "NET-NO",
                                "label": "no", "kind": "agency_network"})
        self.assertEqual(status, 403)
        status, audit = self.call("GET", "/audit", ALICE)
        self.assertEqual(status, 200)
        denied = [e for e in audit["entries"]
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)
        # Audit reads are admin-only.
        status, _b = self.call("GET", "/audit", BOB)
        self.assertEqual(status, 403)

    def test_validation_error_is_400_and_not_found_is_404(self):
        status, _b = self.call("POST", "/organizations", ALICE,
                               {"ref": "has space", "label": "bad"})
        self.assertEqual(status, 400)
        status, _b = self.call("GET", "/routes/rou-99", ALICE)
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
