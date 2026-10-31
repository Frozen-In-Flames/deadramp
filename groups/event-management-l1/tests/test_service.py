"""Core function 11: the REST API, exercised over real HTTP.

Includes the denied-attempt audit discipline: unauthenticated and
forbidden requests are audited with a ``:denied`` suffix, and an
audit read is itself audited (AU-2/AU-3, Low side).
"""

import http.client
import json
import unittest
from urllib.parse import quote

from events.service import make_server

from events_helpers import DURING, ENDS, SESS_ENDS, SESS_STARTS, STARTS

USERS = {"alice": "admin", "bob": "member", "carol": "viewer"}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0, users=USERS)
        self.port = self.server.server_address[1]
        import threading
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
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, payload

    def seed(self):
        status, organizer = self.call(
            "POST", "/organizers", "alice", "admin",
            {"ref": "ORG-0001", "label": "Agency events office"})
        self.assertEqual(status, 201)
        status, vendor = self.call(
            "POST", "/vendors", "alice", "admin",
            {"ref": "VEN-0001", "label": "Vendor Co"})
        self.assertEqual(status, 201)
        status, event = self.call(
            "POST", "/events", "bob", "member",
            {"organizer_id": organizer["id"], "title": "Spring Vendor Day",
             "format": "hybrid", "starts_at": STARTS, "ends_at": ENDS})
        self.assertEqual(status, 201)
        return organizer, vendor, event

    def test_health_is_public(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual((status, payload), (200, {"status": "ok"}))

    def test_full_flow(self):
        organizer, vendor, event = self.seed()
        status, session = self.call(
            "POST", "/sessions", "bob", "member",
            {"event_id": event["id"], "kind": "webinar", "title": "Briefing",
             "starts_at": SESS_STARTS, "ends_at": SESS_ENDS})
        self.assertEqual(status, 201)
        status, round_ = self.call(
            "POST", "/rounds", "bob", "member",
            {"event_id": event["id"], "required_tags": ["cloud", "security"]})
        self.assertEqual(status, 201)
        status, part = self.call(
            "POST", "/rounds/%s/participations" % round_["id"],
            "bob", "member",
            {"vendor_id": vendor["id"],
             "capability_tags": ["cloud", "security", "support"]})
        self.assertEqual(status, 201)
        status, matches = self.call(
            "GET", "/rounds/%s/matches" % round_["id"], "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(matches["match_count"], 1)
        self.assertEqual(matches["matches"][0]["vendor_id"], vendor["id"])
        status, summary = self.call(
            "GET", "/summary?now=%s" % quote(DURING, safe=""),
            "carol", "viewer")
        self.assertEqual(summary["matches_total"], 1)
        self.assertEqual(summary["events_by_status"]["live"], 1)

    def test_bad_format_rejected_over_http(self):
        organizer, _, _ = self.seed()
        status, payload = self.call(
            "POST", "/events", "bob", "member",
            {"organizer_id": organizer["id"], "title": "X",
             "format": "telepathic", "starts_at": STARTS, "ends_at": ENDS})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_auth_and_denied_auditing(self):
        status, _ = self.call("GET", "/organizers")
        self.assertEqual(status, 401)
        status, _ = self.call("POST", "/organizers", "carol", "viewer",
                              {"ref": "X", "label": "Y"})
        self.assertEqual(status, 403)
        status, _ = self.call("GET", "/organizers", "alice", "member")
        self.assertEqual(status, 401)  # role does not match registry
        status, audit = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        denied = [e for e in audit["entries"]
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 3)
        status, _ = self.call("GET", "/audit", "bob", "member")
        self.assertEqual(status, 403)

    def test_unknown_route_and_object(self):
        status, _ = self.call("GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/events/evt-99", "alice", "admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
