"""The REST API over real HTTP — core function 6 (UNION-SPEC.md).

Health is public; missing headers, unknown users, and mismatched
roles are 401; the full flow exercises the decision-basis guard
end to end (a basisless decision is a 400) and the derived intent
status (open, then transformed once a decision cites it); viewer
writes are 403 and audited with a ``:denied`` suffix; the audit
endpoint requires ``audit_read``; 404/405 mapping.
"""

import http.client
import json
import threading
import unittest

from manufacturing.__main__ import DEMO_USERS
from manufacturing.audit import AuditLog
from manufacturing.service import make_server
from manufacturing.store import ManufacturingStore


class Client:
    def __init__(self, port):
        self.port = port

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=10)
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


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        store = ManufacturingStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, store=store,
                                 audit=cls.audit, users=DEMO_USERS)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.client = Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_full_flow(self):
        c = self.client
        status, payload = c.call("GET", "/health")
        self.assertEqual((status, payload["status"]), (200, "ok"))

        # Unauthenticated and self-assigned roles are refused.
        self.assertEqual(c.call("GET", "/organizations")[0], 401)
        self.assertEqual(
            c.call("GET", "/organizations", user="mallory",
                   role="admin")[0], 401)
        self.assertEqual(
            c.call("GET", "/organizations", user="alice",
                   role="viewer")[0], 401)

        status, org = c.call("POST", "/organizations", user="bob",
                             role="operator",
                             body={"ref": "acme-aerospace",
                                   "label": "Acme Aerospace Team"})
        self.assertEqual(status, 201)

        status, intent = c.call(
            "POST", "/intents", user="bob", role="operator",
            body={"org_id": org["id"], "label": "Bracket intent",
                  "statement": "Bracket must hold the shear load.",
                  "author_ref": "eng-1"})
        self.assertEqual(status, 201)
        self.assertEqual(intent["status"], "open")

        # The guard end to end: a basisless decision is a 400 and
        # records nothing.
        status, _ = c.call(
            "POST", "/decisions", user="bob", role="operator",
            body={"org_id": org["id"], "label": "L", "statement": "S",
                  "basis_intent_ids": [], "decided_by_ref": "eng-2"})
        self.assertEqual(status, 400)

        status, decision = c.call(
            "POST", "/decisions", user="bob", role="operator",
            body={"org_id": org["id"], "label": "Bracket decision",
                  "statement": "Machined rib, 6 mm web.",
                  "basis_intent_ids": [intent["id"]],
                  "decided_by_ref": "eng-2"})
        self.assertEqual(status, 201)
        self.assertEqual(decision["id"], "dec-1")

        status, fetched = c.call("GET", "/intents/%s" % intent["id"],
                                 user="carol", role="viewer")
        self.assertEqual((status, fetched["status"]), (200, "transformed"))

        # Viewer writes are 403 and the denial is audited.
        status, _ = c.call(
            "POST", "/intents", user="carol", role="viewer",
            body={"org_id": org["id"], "label": "L", "statement": "S",
                  "author_ref": "eng-9"})
        self.assertEqual(status, 403)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

        # The audit endpoint requires audit_read.
        self.assertEqual(
            c.call("GET", "/audit", user="carol", role="viewer")[0], 403)
        status, audit_payload = c.call("GET", "/audit", user="alice",
                                       role="admin")
        self.assertEqual(status, 200)
        self.assertGreater(audit_payload["count"], 0)

        self.assertEqual(
            c.call("GET", "/nope", user="alice", role="admin")[0], 404)
        self.assertEqual(
            c.call("DELETE", "/organizations", user="alice",
                   role="admin")[0], 405)


if __name__ == "__main__":
    unittest.main()
