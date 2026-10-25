"""REST API service tests.

Traces to: Core function -- REST API; contract for ``comm/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:operator, carol:viewer, dana:auditor},
errors JSON {error} 400/401/403/404, PermissionDenied -> 403 with
'<action>:denied' audit entry, audit_read admin+auditor (AC-5).
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from comm_helpers import USERS
from comm.audit import AuditLog
from comm.service import make_server
from comm.store import CommStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Core: REST API -- real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CommStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        """Core: REST API -- helper performing a real HTTP request."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = None
        hdrs = dict(headers or {})
        if body is not None:
            payload = json.dumps(body)
            hdrs.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        text = raw.decode("utf-8", "replace")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        return status, text, parsed

    def make_contact(self, name="Dana", headers=None):
        """Core: REST API -- helper creating a contact via POST /contacts."""
        status, _, parsed = self.request(
            "POST", "/contacts", headers=headers or BOB,
            body={"name": name, "addresses": {"email": "dana@example.com"}},
        )
        self.assertEqual(status, 201)
        return parsed


class TestHealthAuth(ServiceBase):
    """Core: REST API -- health and header auth."""

    def test_health(self):
        """Core: REST API. GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_401(self):
        """Core: REST API (IA-2). Unknown user or role mismatch -> 401 JSON error."""
        for headers in ({"X-User": "mallory", "X-Role": "admin"},
                        {"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/contacts", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """Core: REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core: REST API -- full communications flow over HTTP."""

    def test_full_flow(self):
        """Core: REST API. contact -> group -> channel -> template -> message -> dispatch-due -> ack -> search -> audit."""
        contact = self.make_contact()
        self.assertTrue(contact["id"].startswith("ct-"))

        status, _, group = self.request("POST", "/groups", headers=BOB, body={"name": "team"})
        self.assertEqual(status, 201)
        status, _, group = self.request(
            "POST", "/groups/%s/members" % group["id"], headers=BOB,
            body={"contact_id": contact["id"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(group["members"], [contact["id"]])

        status, _, members = self.request("GET", "/groups/%s/members" % group["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([m["id"] for m in members["members"]], [contact["id"]])

        # channel_write is admin-only: bob gets 403, alice succeeds.
        status, _, parsed = self.request(
            "POST", "/channels", headers=BOB, body={"kind": "email", "name": "x"}
        )
        self.assertEqual(status, 403)
        status, _, channel = self.request(
            "POST", "/channels", headers=ALICE, body={"kind": "email", "name": "primary"}
        )
        self.assertEqual(status, 201)

        status, _, tpl = self.request(
            "POST", "/templates", headers=BOB,
            body={"name": "w", "subject": "Hi {n}", "body": "Body {n}"},
        )
        self.assertEqual(status, 201)
        status, _, got_tpl = self.request("GET", "/templates/%s" % tpl["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(got_tpl["id"], tpl["id"])

        status, _, msg = self.request(
            "POST", "/messages", headers=BOB,
            body={"template_id": tpl["id"], "variables": {"n": "Dana"},
                  "group_ids": [group["id"]], "channel_kinds": ["email"],
                  "require_ack": True},
        )
        self.assertEqual(status, 201)
        self.assertEqual(msg["subject"], "Hi Dana")

        status, _, deliveries = self.request(
            "GET", "/messages/%s/deliveries" % msg["id"], headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(deliveries["deliveries"]), 1)
        delivery_id = deliveries["deliveries"][0]["id"]

        status, _, summary = self.request("POST", "/dispatch-due", headers=BOB, body={})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(summary["delivered"], 1)

        status, _, ack_status = self.request(
            "GET", "/messages/%s/ack-status" % msg["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(ack_status["total"], 1)
        self.assertEqual(ack_status["acknowledged"], 0)

        status, _, acked = self.request(
            "POST", "/deliveries/%s/ack" % delivery_id, headers=BOB, body={}
        )
        self.assertEqual(status, 200)
        self.assertEqual(acked["status"], "acknowledged")

        query = urllib.parse.urlencode({"q": "dana"})
        status, _, result = self.request("GET", "/search?%s" % query, headers=BOB)
        self.assertEqual(status, 200)
        self.assertTrue(result["contacts"])

        status, _, listing = self.request("GET", "/contacts", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(contact["id"], [c["id"] for c in listing["contacts"]])
        status, _, one = self.request("GET", "/contacts/%s" % contact["id"], headers=CAROL)
        self.assertEqual(status, 200)
        status, _, msgs = self.request("GET", "/messages", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("messages", msgs)
        status, _, chans = self.request("GET", "/channels", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("channels", chans)
        status, _, groups = self.request("GET", "/groups", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("groups", groups)
        status, _, tpls = self.request("GET", "/templates", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("templates", tpls)

    def test_channel_enabled_endpoint_and_message_dispatch(self):
        """Core: REST API. POST /channels/{id}/enabled toggles; POST /messages/{id}/dispatch dispatches that message."""
        contact = self.make_contact(name="Eve-%s" % self.id())
        status, _, channel = self.request(
            "POST", "/channels", headers=ALICE, body={"kind": "email", "name": "toggle"}
        )
        self.assertEqual(status, 201)
        status, _, updated = self.request(
            "POST", "/channels/%s/enabled" % channel["id"], headers=ALICE,
            body={"enabled": False},
        )
        self.assertEqual(status, 200)
        self.assertFalse(updated["enabled"])
        status, _, updated = self.request(
            "POST", "/channels/%s/enabled" % channel["id"], headers=ALICE,
            body={"enabled": True},
        )
        self.assertTrue(updated["enabled"])

        status, _, msg = self.request(
            "POST", "/messages", headers=BOB,
            body={"subject": "S", "body": "B", "contact_ids": [contact["id"]],
                  "channel_kinds": ["email"]},
        )
        self.assertEqual(status, 201)
        status, _, summary = self.request(
            "POST", "/messages/%s/dispatch" % msg["id"], headers=BOB, body={}
        )
        self.assertEqual(status, 200)
        self.assertEqual(summary["delivered"], 1)


class TestServiceAccessAndErrors(ServiceBase):
    """Core: REST API -- 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """Core: REST API / Audit. Viewer POST /contacts -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/contacts", headers=CAROL,
            body={"name": "X", "addresses": {"email": "x@y.z"}},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400_and_not_found_404(self):
        """Core: REST API (SI-10). Bad contact -> 400; unknown contact -> 404."""
        status, _, parsed = self.request(
            "POST", "/contacts", headers=BOB,
            body={"name": "", "addresses": {"email": "x@y.z"}},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/contacts/ct-999999", headers=ALICE)
        self.assertEqual(status, 404)

    def test_audit_admin_and_auditor_only(self):
        """Core: REST API / Audit (AU-6/AC-5). GET /audit -> 403 for
        operator/viewer (operator still denied), 200 for admin and
        for auditor (dana) with {entries}."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)
        status, _, payload = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)


if __name__ == "__main__":
    unittest.main()
