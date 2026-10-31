"""REST API over a live HTTP server.

Traces to: Core 9-adjacent API surface in the UNION-SPEC contract
(the service is API-first) -- health, the 401/403/404 envelopes,
denied attempts audited with ``:denied``, the full research-records
flow, verify-by-content over HTTP, and the digest discipline: a
``query_text`` / ``note_text`` field is hashed by this layer and the
record it produces contains the digest and never the text.
"""

import base64
import hashlib
import http.client
import json
import threading
import unittest

from lawenf.audit import AuditLog
from lawenf.service import make_server
from lawenf.store import LawEnfStore
from lawenf_helpers import (DOC_CONTENT, DOC_SHA256, NOTE_TEXT, QUERY_TEXT,
                            USERS)

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
MALLORY = {"X-User": "mallory", "X-Role": "member"}


class ServiceFixture(unittest.TestCase):
    """Spin the real server on an ephemeral port per test class."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = LawEnfStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, USERS)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestAuthAndEnvelopes(ServiceFixture):
    """Contract: 401/403 envelopes; denials are audited."""

    def test_health_needs_no_auth(self):
        status, body = self.call("GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))

    def test_unknown_user_and_role_mismatch_are_401(self):
        status, _ = self.call("GET", "/matters",
                              {"X-User": "nobody", "X-Role": "member"})
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/matters",
                              {"X-User": "bob", "X-Role": "admin"})
        self.assertEqual(status, 401)

    def test_unknown_route_is_404(self):
        status, body = self.call("GET", "/nope", BOB)
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_denied_attempts_are_audited(self):
        before = [e["action"] for e in self.audit.entries()]
        status, _ = self.call("POST", "/matters", CAROL, {"matter_ref": "X-1"})
        self.assertEqual(status, 403)
        after = [e["action"] for e in self.audit.entries()]
        self.assertEqual(after[len(before):], ["matter_write:denied"])


class TestFullFlow(ServiceFixture):
    """Contract: the whole substrate over HTTP, in dependency order."""

    def test_flow(self):
        # bob opens a matter and adds carol
        status, matter = self.call("POST", "/matters", BOB,
                                   {"matter_ref": "FLOW-REF-1"})
        self.assertEqual(status, 201)
        mid = matter["id"]
        status, matter = self.call("POST", "/matters/%s/members" % mid, BOB,
                                   {"username": "carol"})
        self.assertEqual(status, 200)
        self.assertIn("carol", matter["members"])

        # mallory is authenticated but not a member: 403
        status, _ = self.call("GET", "/matters/%s" % mid, MALLORY)
        self.assertEqual(status, 403)

        # source + document + review lifecycle
        status, src = self.call("POST", "/matters/%s/sources" % mid, BOB, {
            "source_ref": "SRC-1", "kind": "case_law",
            "citation_ref": "CIT-REF-1"})
        self.assertEqual(status, 201)
        status, doc = self.call("POST", "/matters/%s/documents" % mid, BOB, {
            "doc_ref": "DOC-1", "sha256": DOC_SHA256,
            "size_bytes": len(DOC_CONTENT)})
        self.assertEqual(status, 201)
        did = doc["id"]
        status, doc = self.call(
            "POST", "/matters/%s/documents/%s/begin-review" % (mid, did), BOB)
        self.assertEqual((status, doc["status"]), (200, "in_review"))
        status, doc = self.call(
            "POST", "/matters/%s/documents/%s/complete-review" % (mid, did), BOB)
        self.assertEqual((status, doc["status"]), (200, "reviewed"))
        # skipping is a 400
        status, doc2 = self.call("POST", "/matters/%s/documents" % mid, BOB, {
            "doc_ref": "DOC-2", "sha256": DOC_SHA256, "size_bytes": 1})
        status, body = self.call(
            "POST", "/matters/%s/documents/%s/complete-review"
            % (mid, doc2["id"]), BOB)
        self.assertEqual(status, 400)

        # verify-by-content over HTTP: exact bytes match, altered do not
        b64 = base64.b64encode(DOC_CONTENT).decode("ascii")
        status, result = self.call(
            "POST", "/matters/%s/documents/%s/verify" % (mid, did), CAROL,
            {"content_b64": b64})
        self.assertEqual((status, result["matches"]), (200, True))
        b64_bad = base64.b64encode(DOC_CONTENT + b"x").decode("ascii")
        status, result = self.call(
            "POST", "/matters/%s/documents/%s/verify" % (mid, did), CAROL,
            {"content_b64": b64_bad})
        self.assertEqual((status, result["matches"]), (200, False))
        status, _ = self.call(
            "POST", "/matters/%s/documents/%s/verify" % (mid, did), CAROL,
            {"content_b64": "!!!not-base64!!!"})
        self.assertEqual(status, 400)

        # saved search: the text is hashed by the service, never stored
        status, sea = self.call("POST", "/matters/%s/searches" % mid, BOB, {
            "search_ref": "SEA-1", "query_text": QUERY_TEXT, "result_count": 9})
        self.assertEqual(status, 201)
        self.assertEqual(sea["query_sha256"],
                         hashlib.sha256(QUERY_TEXT.encode()).hexdigest())
        self.assertNotIn("query_text", sea)
        self.assertNotIn("query", sea)

        # annotation: same digest discipline for note text
        status, ann = self.call("POST", "/matters/%s/annotations" % mid, BOB, {
            "target_kind": "document", "target_id": did,
            "annotation_ref": "ANN-1", "note_text": NOTE_TEXT})
        self.assertEqual(status, 201)
        self.assertEqual(ann["note_sha256"],
                         hashlib.sha256(NOTE_TEXT.encode()).hexdigest())
        self.assertNotIn("note_text", ann)

        # citation check: treatment verbatim over the wire
        status, chk = self.call(
            "POST", "/matters/%s/citation-checks" % mid, BOB, {
                "citation_ref": "CIT-1", "treatment": "Followed (verbatim)",
                "source_id": src["id"]})
        self.assertEqual((status, chk["treatment"]), (201, "Followed (verbatim)"))

        # report as the viewer-member; audit as member is 403, admin 200
        status, report = self.call("GET", "/matters/%s/report" % mid, CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(report["documents_by_status"], {"reviewed": 1,
                                                         "registered": 1})
        self.assertEqual(report["citation_checks_by_treatment"],
                         {"Followed (verbatim)": 1})
        status, _ = self.call("GET", "/audit", BOB)
        self.assertEqual(status, 403)
        status, body = self.call("GET", "/audit", ALICE)
        self.assertEqual(status, 200)
        actions = [e["action"] for e in body["entries"]]
        self.assertIn("audit_read", actions)

        # registry search over HTTP, membership-scoped
        status, hits = self.call("GET", "/search?q=DOC-1", CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([d["doc_ref"] for d in hits["documents"]], ["DOC-1"])
        status, hits = self.call("GET", "/search?q=DOC-1", MALLORY)
        self.assertEqual(hits["documents"], [])

        # close the matter: further writes are 400
        status, matter = self.call("POST", "/matters/%s/close" % mid, BOB)
        self.assertEqual((status, matter["status"]), (200, "closed"))
        status, _ = self.call("POST", "/matters/%s/sources" % mid, BOB, {
            "source_ref": "SRC-2", "kind": "statute"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
