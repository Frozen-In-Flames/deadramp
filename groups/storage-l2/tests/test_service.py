"""Core function 13: the REST API, exercised over real HTTP.

Includes the denied-attempt audit discipline: unauthenticated and
forbidden requests are audited with a ``:denied`` suffix, and an
audit read is itself audited (AU-2/AU-3/AU-6 at the Moderate
baseline). The full flow exercises the retention gate end to end:
archive, read derived state at two clocks, dispose once eligible.
"""

import http.client
import json
import unittest

from storage.service import make_server

from storage_helpers import AFTER_BOUNDARY, BEFORE_BOUNDARY

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}


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
        status, org = self.call("POST", "/organizations", "alice", "admin",
                                {"ref": "ORG-0001", "label": "Records"})
        self.assertEqual(status, 201)
        status, policy = self.call(
            "POST", "/policies", "alice", "admin",
            {"label": "Standard retention", "retention_days": 30})
        self.assertEqual(status, 201)
        status, collection = self.call(
            "POST", "/collections", "alice", "admin",
            {"org_id": org["id"], "label": "Correspondence",
             "policy_id": policy["id"], "format_label": "native"})
        self.assertEqual(status, 201)
        return org, policy, collection

    def archive_one(self, collection):
        status, message = self.call(
            "POST", "/messages", "bob", "operator",
            {"collection_id": collection["id"], "message_ref": "MSG-1",
             "sender_ref": "SENDER-1", "recipient_refs": ["RECIP-1"],
             "archived_at": "2024-01-01T00:00:00+00:00",
             "size_bytes": 1024, "format_label": "native"})
        self.assertEqual(status, 201)
        return message

    def test_health_is_public(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual((status, payload), (200, {"status": "ok"}))

    def test_full_flow_with_retention_gate(self):
        _, _, collection = self.seed()
        message = self.archive_one(collection)
        # date-only `now` values in query strings: a full ISO
        # offset's "+" would decode to a space under form encoding
        status, view = self.call(
            "GET", "/messages/%s?now=2024-01-15" % message["id"],
            "carol", "viewer")
        self.assertEqual(view["retention_state"], "retained")
        # the gate refuses inside the retention period
        status, payload = self.call(
            "POST", "/messages/%s/dispositions" % message["id"],
            "alice", "admin",
            {"method_label": "shredded", "at": BEFORE_BOUNDARY})
        self.assertEqual(status, 400)
        # and allows it once eligible
        status, disposition = self.call(
            "POST", "/messages/%s/dispositions" % message["id"],
            "alice", "admin",
            {"method_label": "shredded", "at": AFTER_BOUNDARY})
        self.assertEqual(status, 201)
        status, view = self.call(
            "GET", "/messages/%s?now=2024-01-15" % message["id"],
            "carol", "viewer")
        self.assertEqual(view["retention_state"], "disposed")
        status, summary = self.call(
            "GET", "/summary?now=2024-01-15", "carol", "viewer")
        self.assertEqual(summary["dispositions"], 1)
        self.assertEqual(
            summary["messages_by_retention_state"]["disposed"], 1)

    def test_float_and_bool_rejected_over_http(self):
        _, _, collection = self.seed()
        status, _ = self.call(
            "POST", "/messages", "bob", "operator",
            {"collection_id": collection["id"], "message_ref": "MSG-1",
             "sender_ref": "S", "recipient_refs": [],
             "archived_at": "2024-01-01", "size_bytes": 1.5,
             "format_label": "native"})
        self.assertEqual(status, 400)
        status, _ = self.call("POST", "/policies", "alice", "admin",
                              {"label": "bad", "retention_days": True})
        self.assertEqual(status, 400)

    def test_auth_and_denied_auditing(self):
        status, _ = self.call("GET", "/organizations")
        self.assertEqual(status, 401)
        status, _ = self.call("POST", "/organizations", "carol", "viewer",
                              {"ref": "X", "label": "Y"})
        self.assertEqual(status, 403)
        status, _ = self.call("GET", "/organizations", "alice", "operator")
        self.assertEqual(status, 401)  # role does not match registry
        status, audit = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        denied = [e for e in audit["entries"]
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 3)
        status, _ = self.call("GET", "/audit", "bob", "operator")
        self.assertEqual(status, 403)

    def test_unknown_route_and_object(self):
        status, _ = self.call("GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/organizations/org-99",
                              "alice", "admin")
        self.assertEqual(status, 404)

    def test_records_over_http(self):
        org, _, collection = self.seed()
        message = self.archive_one(collection)
        status, custody = self.call(
            "POST", "/custody", "bob", "operator",
            {"org_id": org["id"], "collection_id": collection["id"],
             "custodian_ref": "CUSTODIAN-1", "key_label": "KEY-1"})
        self.assertEqual(status, 201)
        status, discovery = self.call(
            "POST", "/discoveries", "bob", "operator",
            {"matter_ref": "MATTER-1", "collection_id": collection["id"]})
        self.assertEqual(status, 201)
        self.assertEqual(discovery["result_count"], 1)
        status, review = self.call(
            "POST", "/supervision", "bob", "operator",
            {"message_id": message["id"], "reviewer_ref": "REV-1"})
        self.assertEqual(status, 201)
        status, done = self.call(
            "POST", "/supervision/%s/outcome" % review["id"],
            "bob", "operator", {"outcome": "reviewed"})
        self.assertEqual(done["status"], "reviewed")
        status, retrieval = self.call(
            "POST", "/retrievals", "bob", "operator",
            {"message_id": message["id"], "mode": "realtime",
             "destination": "inbox", "requester_ref": "REQ-1"})
        self.assertEqual(status, 201)
        status, found = self.call("GET", "/search?q=sender-1",
                                  "carol", "viewer")
        self.assertEqual(len(found["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
