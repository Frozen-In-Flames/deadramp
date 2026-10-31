"""HTTP service: health, auth denials audited, CRUD round trips."""
import http.client, json, threading, unittest
from librarysys.audit import AuditLog
from librarysys.service import make_server
from librarysys.store import LibrarySysStore
from librarysys.__main__ import DEMO_USERS

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.server = make_server("127.0.0.1", 0, LibrarySysStore(cls.audit), cls.audit, DEMO_USERS)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.server.shutdown()
    def call(self, method, path, user=None, role=None, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if user: headers["X-User"] = user
        if role: headers["X-Role"] = role
        c.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = c.getresponse(); data = json.loads(r.read() or b"{}"); c.close()
        return r.status, data
    def test_health_no_auth(self):
        code, data = self.call("GET", "/health"); self.assertEqual(code, 200)
    def test_unknown_user_denied_and_audited(self):
        code, _ = self.call("GET", "/libraries", "mallory", "admin")
        self.assertEqual(code, 403)
        self.assertTrue(any(e["action"].endswith(":denied") for e in self.audit.entries()))
    def test_round_trip(self):
        code, lib = self.call("POST", "/libraries", "alice", "admin", {"library_ref": "lib-svc", "label": "Svc"})
        self.assertEqual(code, 201)
        code, _ = self.call("POST", "/libraries/%s/members" % lib["id"], "alice", "admin", {"username": "bob"})
        self.assertEqual(code, 200)
        code, item = self.call("POST", "/libraries/%s/items" % lib["id"], "bob", "member", {"item_ref": "item-1", "title": "Work"})
        self.assertEqual(code, 201)
        code, rep = self.call("GET", "/libraries/%s/report" % lib["id"], "bob", "member")
        self.assertEqual(code, 200); self.assertEqual(rep["item_count"], 1)
    def test_viewer_cannot_create_item(self):
        code, lib = self.call("POST", "/libraries", "alice", "admin", {"library_ref": "lib-svc2", "label": "Svc2"})
        self.call("POST", "/libraries/%s/members" % lib["id"], "alice", "admin", {"username": "carol"})
        code, _ = self.call("POST", "/libraries/%s/items" % lib["id"], "carol", "viewer", {"item_ref": "i", "title": "T"})
        self.assertEqual(code, 403)
    def test_audit_endpoint_admin_only(self):
        code, _ = self.call("GET", "/audit", "bob", "member"); self.assertEqual(code, 403)
        code, data = self.call("GET", "/audit", "alice", "admin"); self.assertEqual(code, 200)
if __name__ == "__main__": unittest.main()
