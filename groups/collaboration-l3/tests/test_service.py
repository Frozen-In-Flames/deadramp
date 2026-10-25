"""REST API service tests.

Traces to: UNION-SPEC Core function 9 (API access) / ranking row 1
(APIs, integrations & interoperability, 31 siblings), plus functions
10 (Access control) and 11 (Audit log) as enforced over HTTP;
Implementation contract for ``collab/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
headers matched against the registry, errors as JSON {error} with
400/401/403/404, denied attempts audited with the action name suffixed
``:denied``.
"""

import hashlib
import http.client
import json
import threading
import unittest
import urllib.parse

from collab_helpers import EVENT_END, EVENT_START, USERS_REGISTRY
from collab.audit import AuditLog
from collab.service import make_server
from collab.store import CollabStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DAVE = {"X-User": "dave", "X-Role": "member"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CollabStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS_REGISTRY)
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    # -- low-level helpers -------------------------------------------------
    def request(self, method, path, headers=None, body=None):
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

    # -- flow helpers --------------------------------------------------------
    def create_workspace(self, name, headers=None):
        status, _, parsed = self.request(
            "POST", "/workspaces", headers=headers or BOB,
            body={"name": name},
        )
        self.assertEqual(status, 201, "workspace creation failed")
        self.assertIsInstance(parsed, dict)
        return parsed

    def create_workspace_with_channel(self, name):
        """Bob's workspace with carol as a member and one channel."""
        ws = self.create_workspace(name)
        ws_id = ws["id"]
        status, _, parsed = self.request(
            "POST", "/workspaces/%s/members" % ws_id, headers=BOB,
            body={"username": "carol"},
        )
        self.assertIn(status, (200, 201))
        self.assertIn("carol", parsed["members"])
        status, _, channel = self.request(
            "POST", "/workspaces/%s/channels" % ws_id, headers=BOB,
            body={"name": "general"},
        )
        self.assertEqual(status, 201)
        return ws_id, channel["id"]


class TestHealthAndAuth(ServiceBase):
    """Core: API access — health, header auth, and error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core: API access. Contract: GET /health (no auth) ->
        {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_headers_is_401(self):
        """Core: API access + Access control (IA-2). No X-User/X-Role
        headers -> 401 with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/workspaces")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core: API access (IA-2). Contract: an unknown user -> 401."""
        status, _, parsed = self.request(
            "GET", "/workspaces",
            headers={"X-User": "mallory", "X-Role": "admin"},
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core: API access (IA-2). Contract: 'the role must match the
        registry' — a mismatched X-Role -> 401 (alice claiming viewer,
        bob claiming admin, carol claiming member)."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "member"}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/workspaces",
                                                 headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_json_without_stack_trace(self):
        """Core: API access. Unknown routes return JSON {error} 404,
        and 'no stack trace is ever returned'."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core: API access — the whole collaboration surface over HTTP."""

    def test_full_flow_workspace_to_audit(self):
        """Core: API access + Workspaces/Messaging/Files/Calendaring/
        Search/Notifications/Audit. Full flow: create workspace -> add
        member -> channel -> message with mention -> file -> event ->
        search -> notifications -> mark read -> audit trail present,
        with audit_read forbidden for a member and allowed for admin."""
        ws = self.create_workspace("flow-room")
        ws_id = ws["id"]
        self.assertTrue(ws_id.startswith("ws-"))
        self.assertEqual(ws["owner"], "bob")
        self.assertEqual(ws["members"], ["bob"])

        status, _, ws = self.request(
            "POST", "/workspaces/%s/members" % ws_id, headers=BOB,
            body={"username": "carol"},
        )
        self.assertIn(status, (200, 201))
        self.assertIn("carol", ws["members"])

        status, _, channel = self.request(
            "POST", "/workspaces/%s/channels" % ws_id, headers=BOB,
            body={"name": "general"},
        )
        self.assertEqual(status, 201)
        channel_id = channel["id"]
        self.assertTrue(channel_id.startswith("ch-"))

        status, _, message = self.request(
            "POST",
            "/workspaces/%s/channels/%s/messages" % (ws_id, channel_id),
            headers=BOB,
            body={"text": "@carol standup notes are up"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(message["id"].startswith("msg-"))
        self.assertEqual(message["author"], "bob")

        content = "standup file body"
        status, _, file_rec = self.request(
            "POST", "/workspaces/%s/files" % ws_id, headers=BOB,
            body={"name": "standup-notes.txt", "content": content},
        )
        self.assertEqual(status, 201)
        self.assertEqual(file_rec["version"], 1)
        self.assertEqual(
            file_rec["sha256"],
            hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(file_rec["size_bytes"], len(content.encode("utf-8")))

        status, _, event = self.request(
            "POST", "/workspaces/%s/events" % ws_id, headers=BOB,
            body={"title": "Standup sync", "start": EVENT_START,
                  "end": EVENT_END, "attendees": ["carol"]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(event["id"].startswith("evt-"))

        status, _, listing = self.request(
            "GET", "/workspaces/%s/channels/%s/messages"
            % (ws_id, channel_id),
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        messages = listing["messages"] if isinstance(listing, dict) else listing
        self.assertEqual([m["id"] for m in messages], [message["id"]])

        query = urllib.parse.urlencode({"q": "standup"})
        status, _, result = self.request(
            "GET", "/workspaces/%s/search?%s" % (ws_id, query), headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [m["id"] for m in result["messages"]], [message["id"]]
        )
        self.assertEqual(
            [f["id"] for f in result["files"]], [file_rec["id"]]
        )
        self.assertEqual([e["id"] for e in result["events"]], [event["id"]])

        status, _, payload = self.request(
            "GET", "/notifications", headers=CAROL
        )
        self.assertEqual(status, 200)
        notes = payload["notifications"]
        self.assertEqual(
            sorted(n["kind"] for n in notes),
            ["event_invite", "file_share", "mention"],
        )

        note_id = notes[0]["id"]
        status, _, updated = self.request(
            "POST", "/notifications/%s/read" % note_id, headers=CAROL
        )
        self.assertIn(status, (200, 201))
        self.assertTrue(updated["read"])

        status, _, parsed = self.request("GET", "/audit", headers=BOB)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertIsInstance(entries, list)
        self.assertTrue(entries)
        for entry in entries:
            for key in ("ts", "actor", "action", "target"):
                self.assertIn(key, entry)
        actions = [e["action"] for e in entries]
        for expected in (
            "workspace_create", "member_add", "channel_create",
            "message_post", "file_share", "event_create", "search",
            "notification_read",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_list_and_get_workspace(self):
        """Core: API access + Workspaces. GET /workspaces lists the
        caller's workspaces; GET /workspaces/{id} returns one."""
        ws = self.create_workspace("listable")
        status, _, payload = self.request("GET", "/workspaces", headers=BOB)
        self.assertEqual(status, 200)
        items = payload["workspaces"] if isinstance(payload, dict) else payload
        self.assertIn(ws["id"], [w["id"] for w in items])

        status, _, got = self.request(
            "GET", "/workspaces/%s" % ws["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], ws["id"])
        self.assertEqual(got["name"], "listable")

    def test_get_file_endpoint_returns_content(self):
        """Core: API access + File sharing. GET
        /workspaces/{id}/files/{fid} returns the record plus content,
        readable by another member."""
        ws = self.create_workspace("file-room")
        ws_id = ws["id"]
        self.request(
            "POST", "/workspaces/%s/members" % ws_id, headers=BOB,
            body={"username": "carol"},
        )
        status, _, rec = self.request(
            "POST", "/workspaces/%s/files" % ws_id, headers=BOB,
            body={"name": "doc.txt", "content": "readable body"},
        )
        self.assertEqual(status, 201)
        status, _, got = self.request(
            "GET", "/workspaces/%s/files/%s" % (ws_id, rec["id"]),
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["content"], "readable body")
        self.assertEqual(got["version"], 1)

    def test_presence_endpoints(self):
        """Core: API access + Presence. PUT /presence/{user} sets the
        caller's own presence; GET /presence/{user} reads it back."""
        status, _, rec = self.request(
            "PUT", "/presence/bob", headers=BOB,
            body={"status": "busy", "note": "focus"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(rec["status"], "busy")
        status, _, got = self.request("GET", "/presence/bob", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(got["user"], "bob")
        self.assertEqual(got["status"], "busy")
        self.assertEqual(got["note"], "focus")

    def test_board_endpoints_create_add_move_and_list_cards(self):
        """Core: API access + Whiteboards. POST boards -> 201, POST
        cards -> 201, POST cards/{id}/move updates the position, GET
        cards lists the moved card."""
        ws_id, _ = self.create_workspace_with_channel("board-room")
        status, _, board = self.request(
            "POST", "/workspaces/%s/boards" % ws_id, headers=BOB,
            body={"name": "Sprint"},
        )
        self.assertEqual(status, 201)
        board_id = board["id"]
        self.assertTrue(board_id.startswith("bd-"))

        status, _, card = self.request(
            "POST", "/workspaces/%s/boards/%s/cards" % (ws_id, board_id),
            headers=BOB, body={"text": "drag me", "x": 1, "y": 2},
        )
        self.assertEqual(status, 201)
        self.assertTrue(card["id"].startswith("card-"))

        status, _, moved = self.request(
            "POST",
            "/workspaces/%s/boards/%s/cards/%s/move"
            % (ws_id, board_id, card["id"]),
            headers=BOB, body={"x": 40, "y": 50},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual((moved["x"], moved["y"]), (40, 50))

        status, _, payload = self.request(
            "GET", "/workspaces/%s/boards/%s/cards" % (ws_id, board_id),
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        cards = payload["cards"] if isinstance(payload, dict) else payload
        self.assertEqual([c["id"] for c in cards], [card["id"]])
        self.assertEqual((cards[0]["x"], cards[0]["y"]), (40, 50))

    def test_notifications_endpoint_shape(self):
        """Core: API access + Notifications. GET /notifications returns
        {"notifications": [...]} for the caller (empty when none)."""
        status, _, payload = self.request(
            "GET", "/notifications", headers=DAVE
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["notifications"], [])


class TestServiceAccessControlAndAudit(ServiceBase):
    """Core: API access — permission enforcement and audit over HTTP."""

    def test_viewer_posting_a_message_is_403(self):
        """Core: Access control (AC-3). A viewer workspace member
        POSTing a message -> 403 JSON {error} (viewer lacks post)."""
        ws_id, channel_id = self.create_workspace_with_channel("viewer-room")
        status, _, parsed = self.request(
            "POST",
            "/workspaces/%s/channels/%s/messages" % (ws_id, channel_id),
            headers=CAROL, body={"text": "viewer attempt"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_cannot_create_a_workspace(self):
        """Core: Access control. Viewer POST /workspaces -> 403 (viewer
        lacks create_workspace)."""
        status, _, parsed = self.request(
            "POST", "/workspaces", headers=CAROL, body={"name": "nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_non_member_getting_a_workspace_is_403(self):
        """Core: Access control (AC-3). Dave belongs to no workspace
        here: GET /workspaces/{id} -> 403 JSON {error}."""
        ws_id, _ = self.create_workspace_with_channel("private-room")
        status, _, parsed = self.request(
            "GET", "/workspaces/%s" % ws_id, headers=DAVE
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_get_unknown_workspace_is_404(self):
        """Core: API access. Unknown workspace id -> 404 JSON {error}."""
        status, _, parsed = self.request(
            "GET", "/workspaces/ws-999999", headers=ALICE
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_invalid_event_is_400(self):
        """Core: API access + Calendaring (SI-10). An event whose end
        is not after its start -> 400 JSON {error}."""
        ws_id, _ = self.create_workspace_with_channel("bad-event-room")
        status, _, parsed = self.request(
            "POST", "/workspaces/%s/events" % ws_id, headers=BOB,
            body={"title": "backwards", "start": EVENT_END,
                  "end": EVENT_START},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_presence_for_another_user_is_403_and_invalid_status_400(self):
        """Core: API access + Presence. PUT /presence/bob as carol ->
        403 (store enforces self-or-admin); an invalid status as bob
        -> 400."""
        status, _, parsed = self.request(
            "PUT", "/presence/bob", headers=CAROL, body={"status": "busy"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        status, _, parsed = self.request(
            "PUT", "/presence/bob", headers=BOB, body={"status": "away"}
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_member_and_viewer_cannot_read_audit(self):
        """Core: Access control + Audit log (AU-6). audit_read is
        admin-only: member and viewer GET /audit -> 403."""
        for headers in (BOB, CAROL):
            with self.subTest(headers=headers):
                status, _, parsed = self.request(
                    "GET", "/audit", headers=headers
                )
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)

    def test_denied_attempt_appears_in_audit_with_denied_suffix(self):
        """Core: Audit log. Contract: 'denied attempts (401 and 403)
        are audited with the action name suffixed :denied' — after
        carol's 403 post attempt, admin's audit read contains a carol
        entry whose action ends with :denied."""
        ws_id, channel_id = self.create_workspace_with_channel("denied-room")

        def carol_denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            entries = (payload["entries"] if isinstance(payload, dict)
                       else payload)
            return len([
                e for e in entries
                if e["actor"] == "carol"
                and str(e["action"]).endswith(":denied")
            ])

        before = carol_denied_count()
        status, _, _ = self.request(
            "POST",
            "/workspaces/%s/channels/%s/messages" % (ws_id, channel_id),
            headers=CAROL, body={"text": "denied attempt"},
        )
        self.assertEqual(status, 403)
        self.assertGreater(carol_denied_count(), before)


class TestAuditorOverHttp(ServiceBase):
    """Core: Access control (AC-5) + Audit log (AU-6/AU-9) — the
    auditor demo user dana over HTTP."""

    def test_auditor_can_read_audit(self):
        """AC-5/AU-6: dana (auditor) GET /audit -> 200 with entries."""
        status, _, payload = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)
        self.assertIn("entries", payload)

    def test_auditor_cannot_create_workspace(self):
        """AC-5: dana POST /workspaces -> 403 (auditor lacks
        create_workspace)."""
        status, _, parsed = self.request(
            "POST", "/workspaces", headers=DANA, body={"name": "nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_auditor_cannot_list_workspaces(self):
        """AC-5: dana GET /workspaces -> 403 (auditor lacks "read")."""
        status, _, parsed = self.request("GET", "/workspaces", headers=DANA)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_audit_verify_as_auditor_ok(self):
        """AU-9: GET /audit/verify as dana -> 200 with ok True."""
        status, _, parsed = self.request("GET", "/audit/verify", headers=DANA)
        self.assertEqual(status, 200)
        self.assertTrue(parsed["ok"])
        self.assertIsNone(parsed["first_bad_index"])
        self.assertIn("entries", parsed)

    def test_audit_verify_as_member_forbidden(self):
        """AU-6: GET /audit/verify as bob (member, no audit_read) -> 403."""
        status, _, parsed = self.request("GET", "/audit/verify", headers=BOB)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
