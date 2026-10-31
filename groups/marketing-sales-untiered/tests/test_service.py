"""Core function 14: the REST API, exercised over real HTTP.

Includes the denied-attempt audit discipline: unauthenticated and
forbidden requests are audited with a ``:denied`` suffix, and an
audit read is itself audited. The full flow exercises the
suppression gate end to end: campaign, suppression, a refused
delivery (400), a recorded delivery, an engagement, the report.
"""

import http.client
import json
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marketsales.service import make_server  # noqa: E402

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
OCCURRED = "2026-01-10T10:00:00+00:00"


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0, users=USERS)
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
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, payload

    def seed_campaign(self):
        status, org = self.call("POST", "/organizations", "alice", "admin",
                                {"ref": "ORG-1", "label": "Outreach"})
        self.assertEqual(status, 201)
        status, lst = self.call("POST", "/lists", "bob", "operator",
                                {"org_id": org["id"], "label": "Contacts",
                                 "contact_count": 10})
        self.assertEqual(status, 201)
        status, seg = self.call("POST", "/segments", "bob", "operator",
                                {"org_id": org["id"], "label": "All",
                                 "basis_label": "loaded list",
                                 "member_count": 10})
        self.assertEqual(status, 201)
        status, cam = self.call("POST", "/campaigns", "bob", "operator",
                                {"org_id": org["id"], "label": "News",
                                 "segment_id": seg["id"],
                                 "list_id": lst["id"],
                                 "scheduled_for": "2026-01-10T09:00:00+00:00"})
        self.assertEqual(status, 201)
        return org, lst, cam

    def test_health_is_public(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual((status, payload), (200, {"status": "ok"}))

    def test_authentication_and_role_match(self):
        status, _ = self.call("GET", "/organizations")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations", "alice", "viewer")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations", "mallory", "admin")
        self.assertEqual(status, 401)

    def test_full_flow_with_suppression_gate(self):
        _org, lst, cam = self.seed_campaign()
        self.assertEqual(cam["status"], "scheduled")
        status, sup = self.call("POST", "/suppressions", "bob", "operator",
                                {"list_id": lst["id"],
                                 "contact_ref": "CONTACT-REF-9",
                                 "reason": "unsubscribe"})
        self.assertEqual(status, 201)
        status, payload = self.call(
            "POST", "/deliveries", "bob", "operator",
            {"campaign_id": cam["id"], "contact_ref": "CONTACT-REF-9",
             "outcome": "delivered", "occurred_at": OCCURRED})
        self.assertEqual(status, 400)
        self.assertIn("suppression", payload["error"])
        status, dlv = self.call(
            "POST", "/deliveries", "bob", "operator",
            {"campaign_id": cam["id"], "contact_ref": "CONTACT-REF-1",
             "outcome": "delivered", "occurred_at": OCCURRED})
        self.assertEqual(status, 201)
        status, _eng = self.call(
            "POST", "/engagements", "bob", "operator",
            {"campaign_id": cam["id"], "contact_ref": "CONTACT-REF-1",
             "kind": "open", "occurred_at": OCCURRED})
        self.assertEqual(status, 201)
        status, report = self.call("GET", "/campaigns/%s/report" % cam["id"],
                                   "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(report["status"], "reported")
        self.assertEqual(report["deliveries_by_outcome"]["delivered"], 1)
        status, check = self.call(
            "GET", "/suppression-check?list_id=%s&contact_ref=CONTACT-REF-9"
            % lst["id"], "carol", "viewer")
        self.assertEqual(check, {"suppressed": True})

    def test_viewer_write_is_forbidden_and_audited(self):
        status, _ = self.call("POST", "/organizations", "carol", "viewer",
                              {"ref": "ORG-9", "label": "Nope"})
        self.assertEqual(status, 403)
        status, _first = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        # An audit read is itself audited, so the second read shows
        # both the denied attempt and the first read.
        status, audit = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in audit["entries"]]
        self.assertTrue(any(a.endswith(":denied") for a in actions))
        self.assertIn("audit_read", actions)

    def test_not_found_and_validation_errors(self):
        status, _ = self.call("GET", "/campaigns/cam-99", "alice", "admin")
        self.assertEqual(status, 404)
        status, _ = self.call("POST", "/organizations", "alice", "admin",
                              {"ref": "", "label": "x"})
        self.assertEqual(status, 400)
        status, _ = self.call("GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
