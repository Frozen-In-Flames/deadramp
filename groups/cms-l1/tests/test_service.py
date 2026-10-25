"""REST API service tests.

Traces to: Core function -- REST API (the service surface over the 9
substrate functions); contract for ``cms/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:publisher, carol:editor, dave:author,
erin:viewer}, errors JSON {error} 400/401/403/404, creates 201,
GET /health unauthenticated, GET /audit admin-only (audit_read).
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from cms_helpers import USERS
from cms.audit import AuditLog
from cms.service import make_server
from cms.store import CmsStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "publisher"}
CAROL = {"X-User": "carol", "X-Role": "editor"}
DAVE = {"X-User": "dave", "X-Role": "author"}
ERIN = {"X-User": "erin", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Core: REST API -- real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CmsStore(audit=cls.audit)
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

    def make_site(self, slug=None):
        """Core: REST API -- helper creating a site via POST /sites."""
        slug = slug or ("site-%s" % self.id().rsplit(".", 1)[-1].lower().replace("_", "-"))
        status, _, parsed = self.request(
            "POST", "/sites", headers=BOB,
            body={"name": "Site %s" % slug, "slug": slug, "description": "d"})
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
                        {"X-User": "dave", "X-Role": "admin"}, {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/sites", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """Core: REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core: REST API -- full CMS flow over HTTP (delivery_publishing)."""

    def test_full_flow(self):
        """Core: REST API. site -> section -> type -> tag -> item (dave) -> update -> submit -> approve (carol) -> publish (bob, windowed) -> publishes -> item window at pinned now -> archive -> asset -> search -> report -> audit (alice)."""
        site = self.make_site()
        status, _, section = self.request(
            "POST", "/sites/%s/sections" % site["id"], headers=CAROL,
            body={"name": "News", "slug": "news-%s" % site["id"]})
        self.assertEqual(status, 201)
        status, _, sections = self.request("GET", "/sites/%s/sections" % site["id"], headers=ERIN)
        self.assertEqual(status, 200)
        self.assertEqual(len(sections["sections"]), 1)

        status, _, types = self.request("GET", "/types", headers=ERIN)
        self.assertEqual(status, 200)
        self.assertIn("ct-article", [t["id"] for t in types["types"]])
        status, _, ctype = self.request(
            "POST", "/types", headers=BOB, body={"name": "flow-type-%s" % site["id"]})
        self.assertEqual(status, 201)

        status, _, tag = self.request(
            "POST", "/tags", headers=CAROL,
            body={"name": "Flow", "slug": "flow-%s" % site["id"]})
        self.assertEqual(status, 201)

        status, _, item = self.request(
            "POST", "/items", headers=DAVE,
            body={"site_id": site["id"], "type_id": "ct-article",
                  "title": "Flow Post", "slug": "flow-post-%s" % site["id"],
                  "body": "hello flow", "section_id": section["id"],
                  "metadata": {"topic": "flow"}, "tag_ids": [tag["id"]]})
        self.assertEqual(status, 201)
        self.assertEqual(item["status"], "draft")
        self.assertEqual(item["author"], "dave")

        status, _, updated = self.request(
            "PATCH", "/items/%s" % item["id"], headers=DAVE, body={"body": "hello flow v2"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        status, _, revs = self.request("GET", "/items/%s/revisions" % item["id"], headers=ERIN)
        self.assertEqual(status, 200)
        self.assertEqual(len(revs["revisions"]), 2)

        status, _, submitted = self.request("POST", "/items/%s/submit" % item["id"], headers=DAVE)
        self.assertEqual(status, 200)
        self.assertEqual(submitted["status"], "in_review")

        # Author trying to approve over HTTP: item_review is not an author action -> 403.
        status, _, parsed = self.request("POST", "/items/%s/approve" % item["id"], headers=DAVE)
        self.assertEqual(status, 403)

        status, _, approved = self.request("POST", "/items/%s/approve" % item["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(approved["status"], "approved")

        status, _, published = self.request(
            "POST", "/items/%s/publish" % item["id"], headers=BOB,
            body={"publish_at": "2026-06-10T00:00:00+00:00",
                  "expire_at": "2026-06-20T00:00:00+00:00"})
        self.assertEqual(status, 200)
        self.assertEqual(published["status"], "published")

        status, _, pubs = self.request("GET", "/publishes", headers=ERIN)
        self.assertEqual(status, 200)
        self.assertTrue(any(p["item_id"] == item["id"] for p in pubs["publishes"]))

        query = urllib.parse.urlencode({"now": "2026-06-15T12:00:00+00:00"})
        status, _, got = self.request("GET", "/items/%s?%s" % (item["id"], query), headers=ERIN)
        self.assertEqual(status, 200)
        self.assertEqual(got["window_state"], "live")
        self.assertTrue(got["is_live"])

        status, _, asset = self.request(
            "POST", "/assets", headers=DAVE,
            body={"site_id": site["id"], "filename": "flow.png", "kind": "image",
                  "byte_size": 3, "data": "abc"})
        self.assertEqual(status, 201)
        self.assertTrue(asset["content_sha256"])

        query = urllib.parse.urlencode({"q": "flow"})
        status, _, result = self.request("GET", "/search?%s" % query, headers=ERIN)
        self.assertEqual(status, 200)
        self.assertEqual(set(result.keys()), {"items", "assets", "sites", "tags"})
        self.assertTrue(result["items"])

        status, _, report = self.request("GET", "/report", headers=ERIN)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(report["totals"]["items"], 1)
        self.assertGreaterEqual(report["publish_records"], 1)

        status, _, archived = self.request("POST", "/items/%s/archive" % item["id"], headers=BOB)
        self.assertEqual(status, 200)
        self.assertEqual(archived["status"], "archived")

        status, _, audit_payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertTrue(audit_payload["entries"])

    def test_audit_forbidden_for_non_admin(self):
        """Core: REST API / Audit (AU-6). GET /audit -> 403 for publisher/editor/author/viewer."""
        for headers in (BOB, CAROL, DAVE, ERIN):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/audit", headers=headers)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)

    def test_return_flow_over_http(self):
        """Core: REST API. submit -> return (with note) -> draft over HTTP."""
        site = self.make_site()
        status, _, item = self.request(
            "POST", "/items", headers=DAVE,
            body={"site_id": site["id"], "type_id": "ct-page",
                  "title": "Returnable", "slug": "returnable-%s" % site["id"]})
        self.assertEqual(status, 201)
        self.request("POST", "/items/%s/submit" % item["id"], headers=DAVE)
        status, _, returned = self.request(
            "POST", "/items/%s/return" % item["id"], headers=CAROL, body={"note": "fix it"})
        self.assertEqual(status, 200)
        self.assertEqual(returned["status"], "draft")
        self.assertEqual(returned["return_note"], "fix it")


class TestServiceAccessAndErrors(ServiceBase):
    """Core: REST API -- 400/403/404 and denied-audit behaviour."""

    def test_viewer_site_create_403_and_denied_audited(self):
        """Core: REST API / Audit. Viewer POST /sites -> 403, and a ':denied' audit entry appears for erin."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "erin" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/sites", headers=ERIN, body={"name": "X", "slug": "x-denied"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400(self):
        """Core: REST API (SI-10). Bad slug -> 400 JSON error."""
        status, _, parsed = self.request(
            "POST", "/sites", headers=BOB, body={"name": "Bad", "slug": "BAD SLUG"})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_not_found_404(self):
        """Core: REST API. Unknown item id -> 404 JSON error."""
        status, _, parsed = self.request("GET", "/items/ci-999999", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
