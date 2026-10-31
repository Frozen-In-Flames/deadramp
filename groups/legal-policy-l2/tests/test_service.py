"""REST API over a live HTTP server.

Traces to: the UNION-SPEC service contract — health with no auth,
the 401/403/400/404 JSON ``{error}`` envelopes, denied attempts
audited with the action suffixed ``:denied``, audit_read admin-only
and itself audited, the full records flow over HTTP, the sandbox
single-use rule over HTTP (second execution is a 400), and the
digest discipline: a ``query_text`` field is hashed by this layer
and the record it produces — in the response and in the store —
contains the digest and never the text.
"""

import base64
import hashlib
import http.client
import json
import threading
import unittest

import legalpol_helpers as H
from legalpol.audit import AuditLog
from legalpol.service import make_server
from legalpol.store import LegalPolStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DAVE = {"X-User": "dave", "X-Role": "member"}


class ServiceFixture(unittest.TestCase):
    """Spin the real server on an ephemeral port per test class."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = LegalPolStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(H.USERS_REGISTRY))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      kwargs={"poll_interval": 0.05})
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestAuthAndEnvelopes(ServiceFixture):
    """Contract: 401/403/404 envelopes; denials are audited."""

    def test_health_needs_no_auth(self):
        """Service: GET /health is 200 {"status": "ok"} with no auth."""
        status, body = self.call("GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))

    def test_unknown_user_and_role_mismatch_are_401(self):
        """Service: unknown users and role mismatches are 401, and
        the denial is audited with a ``:denied`` suffix."""
        status, body = self.call("GET", "/agencies",
                                 {"X-User": "nobody", "X-Role": "member"})
        self.assertEqual(status, 401)
        self.assertIn("error", body)
        status, _ = self.call("GET", "/agencies",
                              {"X-User": "bob", "X-Role": "admin"})
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/agencies")
        self.assertEqual(status, 401)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

    def test_unknown_route_is_404(self):
        """Service: an unknown route is a 404 JSON error."""
        status, body = self.call("GET", "/nope", BOB)
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_validation_error_is_400(self):
        """Service: a validation failure (member creating an agency
        is a 403; a malformed agency body from admin is a 400)."""
        status, body = self.call("POST", "/agencies", ALICE,
                                 {"agency_ref": "", "label": "Bad"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_permission_error_is_403_and_audited(self):
        """Service: a member creating an agency is 403 (agency_write
        is admin-only) and the denial is audited."""
        before = len([e for e in self.audit.entries()
                      if e["action"].endswith(":denied")])
        status, body = self.call("POST", "/agencies", BOB,
                                 {"agency_ref": "AGY-X", "label": "Nope"})
        self.assertEqual(status, 403)
        self.assertIn("error", body)
        after = len([e for e in self.audit.entries()
                     if e["action"].endswith(":denied")])
        self.assertEqual(after, before + 1)


class TestFullFlow(ServiceFixture):
    """Contract: the whole substrate over HTTP, in dependency order."""

    def test_flow(self):
        # agency by admin; bob and carol added as members
        status, agency = self.call("POST", "/agencies", ALICE, {
            "agency_ref": "FLOW-AGY-1", "label": "Flow Agency"})
        self.assertEqual(status, 201)
        aid = agency["id"]
        for username in ("bob", "carol"):
            status, agency = self.call(
                "POST", "/agencies/%s/members" % aid, ALICE,
                {"username": username})
            self.assertEqual(status, 200)
        self.assertEqual(agency["members"], ["alice", "bob", "carol"])

        # dave is authenticated but not a member: 403
        status, _ = self.call("GET", "/agencies/%s" % aid, DAVE)
        self.assertEqual(status, 403)
        # carol (viewer) cannot create a workspace: 403
        status, _ = self.call("POST", "/agencies/%s/workspaces" % aid,
                              CAROL, {"workspace_ref": "W-0", "title": "No"})
        self.assertEqual(status, 403)

        # workspace + sandbox session (create returns stored shape)
        status, workspace = self.call(
            "POST", "/agencies/%s/workspaces" % aid, BOB,
            {"workspace_ref": "FLOW-WSP-1", "title": "Flow Workspace"})
        self.assertEqual(status, 201)
        wid = workspace["id"]
        status, session = self.call(
            "POST", "/agencies/%s/sessions" % aid, BOB, {
                "workspace_id": wid, "session_ref": "FLOW-SES-1",
                "sandbox": True})
        self.assertEqual(status, 201)
        self.assertNotIn("expired", session)
        self.assertNotIn("sandbox_consumed", session)
        sid = session["id"]

        # single-use over HTTP: first execution 201, second 400
        status, execution = self.call(
            "POST", "/agencies/%s/sessions/%s/executions" % (aid, sid), BOB,
            {"execution_ref": "EXE-1", "language": "python"})
        self.assertEqual(status, 201)
        status, body = self.call(
            "POST", "/agencies/%s/sessions/%s/executions" % (aid, sid), BOB,
            {"execution_ref": "EXE-2"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

        # the list view derives both flags
        status, payload = self.call("GET", "/agencies/%s/sessions" % aid, BOB)
        self.assertEqual(status, 200)
        view = payload["sessions"][0]
        self.assertFalse(view["expired"])
        self.assertTrue(view["sandbox_consumed"])

        # library over HTTP (platform registry)
        status, source = self.call("POST", "/library", BOB, {
            "source_ref": "FLOW-LIB-1", "kind": "regulation",
            "title": "Flow Regulation"})
        self.assertEqual(status, 201)
        status, payload = self.call("GET", "/library?kind=regulation", CAROL)
        self.assertEqual([s["source_ref"] for s in payload["sources"]],
                         ["FLOW-LIB-1"])

        # saved search: the text is hashed by the service, never stored
        status, search = self.call(
            "POST", "/agencies/%s/searches" % aid, BOB, {
                "search_ref": "SEA-1", "query_text": H.QUERY_TEXT,
                "result_count": 9, "workspace_id": wid})
        self.assertEqual(status, 201)
        expected = hashlib.sha256(H.QUERY_TEXT.encode("utf-8")).hexdigest()
        self.assertEqual(search["query_sha256"], expected)
        stored = self.store._searches[search["id"]]
        self.assertEqual(stored["query_sha256"], expected)
        for value in stored.values():
            if isinstance(value, str):
                self.assertNotIn(H.QUERY_TEXT, value)
        # query_sha256 may also be supplied directly
        status, search2 = self.call(
            "POST", "/agencies/%s/searches" % aid, BOB, {
                "search_ref": "SEA-2", "query_sha256": H.SHA256_A,
                "result_count": 0})
        self.assertEqual(status, 201)
        self.assertEqual(search2["query_sha256"], H.SHA256_A)

        # document + verify-by-content over HTTP
        status, doc = self.call(
            "POST", "/agencies/%s/documents" % aid, BOB, {
                "workspace_id": wid, "doc_ref": "DOC-1",
                "sha256": H.DOC_SHA256, "size_bytes": len(H.DOC_CONTENT),
                "session_id": sid})
        self.assertEqual(status, 201)
        did = doc["id"]
        b64 = base64.b64encode(H.DOC_CONTENT).decode("ascii")
        status, result = self.call(
            "POST", "/agencies/%s/documents/%s/verify" % (aid, did), CAROL,
            {"content_b64": b64})
        self.assertEqual((status, result["matches"]), (200, True))
        b64_bad = base64.b64encode(H.DOC_CONTENT + b"x").decode("ascii")
        status, result = self.call(
            "POST", "/agencies/%s/documents/%s/verify" % (aid, did), CAROL,
            {"content_b64": b64_bad})
        self.assertEqual((status, result["matches"]), (200, False))
        status, _ = self.call(
            "POST", "/agencies/%s/documents/%s/verify" % (aid, did), CAROL,
            {"content_b64": "!!!not-base64!!!"})
        self.assertEqual(status, 400)

        # usage quantity discipline over HTTP: a float is a 400
        status, _ = self.call("POST", "/agencies/%s/usage" % aid, BOB, {
            "usage_ref": "USE-BAD", "kind": "search", "quantity": 1.5})
        self.assertEqual(status, 400)
        status, usage = self.call("POST", "/agencies/%s/usage" % aid, BOB, {
            "usage_ref": "USE-1", "kind": "search", "quantity": 9})
        self.assertEqual(status, 201)

        # export manifest over HTTP
        status, export = self.call("POST", "/agencies/%s/exports" % aid,
                                   BOB, {"export_ref": "EXP-1"})
        self.assertEqual(status, 201)
        self.assertEqual(export["record_count"], 1)
        self.assertEqual(export["total_quantity"], 9)
        self.assertEqual(len(export["checksum"]), 64)

        # report as the viewer-member; registry search over HTTP
        status, report = self.call("GET", "/agencies/%s/report" % aid, CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(report["execution_count"], 1)
        self.assertEqual(report["sandbox_sessions_consumed"], 1)
        status, hits = self.call("GET", "/search?q=DOC-1", CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([d["doc_ref"] for d in hits["documents"]], ["DOC-1"])
        status, hits = self.call("GET", "/search?q=DOC-1", DAVE)
        self.assertEqual(hits["documents"], [])

        # close the session; further executions are a 400
        status, closed = self.call(
            "POST", "/agencies/%s/sessions/%s/close" % (aid, sid), BOB)
        self.assertEqual((status, closed["status"]), (200, "closed"))

        # audit: member 403, admin 200 and the read itself is audited
        status, _ = self.call("GET", "/audit", BOB)
        self.assertEqual(status, 403)
        status, body = self.call("GET", "/audit", ALICE)
        self.assertEqual(status, 200)
        actions = [e["action"] for e in body["entries"]]
        self.assertIn("audit_read", actions)
        self.assertTrue(any(a.endswith(":denied") for a in actions))


if __name__ == "__main__":
    unittest.main()
