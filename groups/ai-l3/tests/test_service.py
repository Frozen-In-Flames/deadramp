"""REST API service tests.

Traces to: UNION-SPEC Core function 8 (API access), plus functions 9
(Access control & API keys) and 10 (Audit log) as enforced over HTTP;
Implementation contract for ``aigateway/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
headers matched against the registry, errors as JSON {error} with
400/401/403/404/422/429, denied attempts (401, 403, 422, 429) audited
with the action name suffixed ``:denied``, and no stack trace ever
returned. The completion endpoint is OpenAI-flavored, this build's own
API — and every completion it returns is labeled a reference stub.
"""

import http.client
import json
import threading
import unittest

from aigateway_helpers import USERS_REGISTRY
from aigateway.audit import AuditLog
from aigateway.service import make_server
from aigateway.store import AIGatewayStore, REFERENCE_NOTICE

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = AIGatewayStore(audit=cls.audit)
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

    def create_model(self, name, responder="echo", config=None, headers=None):
        body = {"name": name, "responder": responder}
        if config is not None:
            body["config"] = config
        status, _, parsed = self.request(
            "POST", "/models", headers=headers or ALICE, body=body
        )
        self.assertEqual(status, 201, "model creation failed: %r" % (parsed,))
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core function 8: API access — health, header auth, error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core 8: GET /health (no auth) -> {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_is_401(self):
        """Core 8+9 (IA-2): no X-User/X-Role headers -> 401 JSON
        {error}."""
        status, _, parsed = self.request("GET", "/models")
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core 8+9: an unknown user -> 401."""
        status, _, parsed = self.request(
            "GET", "/models", headers={"X-User": "mallory", "X-Role": "admin"}
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core 8+9: the role must match the registry — a mismatched
        X-Role -> 401."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "member"}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/models",
                                                 headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_without_stack_trace(self):
        """Core 8: unknown routes return JSON {error} 404 and no
        stack trace is ever returned."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestModelAndTemplateEndpoints(ServiceBase):
    """Core functions 8, 1, 2: registry endpoints over HTTP."""

    def test_model_lifecycle_over_http(self):
        """Core 8+1: POST /models -> 201, GET /models lists, GET
        /models/{name} returns the latest version, GET
        /models/{name}/versions/{v} a specific one, POST
        .../versions/{v}/status flips its status."""
        model = self.create_model("http-echo")
        self.assertEqual(model["id"], "mdl-1")
        self.assertEqual(model["status"], "active")
        self.create_model("http-echo", responder="template",
                          config={"template": "V2: {prompt}"})

        status, _, payload = self.request("GET", "/models", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["models"]), 2)

        status, _, latest = self.request("GET", "/models/http-echo", headers=BOB)
        self.assertEqual(status, 200)
        self.assertEqual(latest["version"], 2)

        status, _, v1 = self.request(
            "GET", "/models/http-echo/versions/1", headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(v1["responder"], "echo")

        status, _, updated = self.request(
            "POST", "/models/http-echo/versions/1/status", headers=ALICE,
            body={"status": "deprecated"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["status"], "deprecated")

    def test_model_not_found_is_404_and_invalid_is_400(self):
        """Core 8+1 (SI-10): unknown model -> 404; an invalid
        responder -> 400, both JSON {error}."""
        status, _, parsed = self.request("GET", "/models/ghost", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        status, _, parsed = self.request(
            "POST", "/models", headers=ALICE,
            body={"name": "bad", "responder": "neural"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_viewer_cannot_create_model_is_403(self):
        """Core 8+9 (AC-3): a viewer POST /models -> 403."""
        status, _, parsed = self.request(
            "POST", "/models", headers=CAROL,
            body={"name": "viewer-model", "responder": "echo"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_template_endpoints(self):
        """Core 8+2: POST /templates -> 201; GET /templates lists."""
        status, _, tpl = self.request(
            "POST", "/templates", headers=BOB,
            body={"name": "wrap", "text": "Please: {prompt}"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(tpl["id"], "tpl-1")
        status, _, payload = self.request("GET", "/templates", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([t["name"] for t in payload["templates"]], ["wrap"])


class TestCompletionFlow(ServiceBase):
    """Core functions 8, 3, 4, 5, 6: the gateway over HTTP."""

    def setUp(self):
        self.create_model("svc-echo-" + self._testMethodName)

    def _model_name(self):
        return "svc-echo-" + self._testMethodName

    def test_completion_is_201_and_labeled_stub(self):
        """Core 8+3: POST /v1/completions -> 201 with the request
        dict; the response carries reference_stub true and the exact
        REFERENCE_NOTICE (this build's own API, stub responder)."""
        status, _, record = self.request(
            "POST", "/v1/completions", headers=BOB,
            body={"model": self._model_name(), "prompt": "ping"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(record["output"], "ping")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["notice"], REFERENCE_NOTICE)
        self.assertEqual(record["status"], "completed")

    def test_completion_viewer_is_403(self):
        """Core 8+9: a viewer lacks invoke — POST /v1/completions
        -> 403."""
        status, _, parsed = self.request(
            "POST", "/v1/completions", headers=CAROL,
            body={"model": self._model_name(), "prompt": "ping"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_completion_unknown_model_is_404(self):
        """Core 8+3: an unknown model in a completion -> 404."""
        status, _, parsed = self.request(
            "POST", "/v1/completions", headers=BOB,
            body={"model": "ghost-model", "prompt": "ping"},
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_policy_blocked_completion_is_422(self):
        """Core 8+6: a policy-blocked completion -> 422 JSON
        {error}; the blocked record is retrievable by its actor."""
        status, _, rule = self.request(
            "POST", "/policy/rules", headers=ALICE,
            body={"scope": "input", "kind": "term",
                  "value": "blocked-" + self._testMethodName},
        )
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "POST", "/v1/completions", headers=BOB,
            body={"model": self._model_name(),
                  "prompt": "has blocked-" + self._testMethodName},
        )
        self.assertEqual(status, 422)
        self.assertIn("error", parsed)
        # Denied attempts (422 included) are audited by the service
        # layer with the action name suffixed ':denied'.
        denied = [e for e in self.audit.entries()
                  if e["action"] == "invoke:denied" and e["actor"] == "bob"]
        self.assertTrue(denied)
        status, _, payload = self.request("GET", "/requests", headers=BOB)
        self.assertEqual(status, 200)
        mine = [r for r in payload["requests"]
                if r["model"] == self._model_name()]
        self.assertEqual([r["status"] for r in mine], ["blocked_input"])

    def test_quota_exceeded_completion_is_429(self):
        """Core 8+4: a completion that would exceed the owner's
        quota -> 429 JSON {error}."""
        status, _, _ = self.request(
            "POST", "/quotas", headers=ALICE,
            body={"owner": "bob", "token_limit": 1},
        )
        self.assertEqual(status, 200)
        try:
            status, _, parsed = self.request(
                "POST", "/v1/completions", headers=BOB,
                body={"model": self._model_name(),
                      "prompt": "a much longer prompt"},
            )
            self.assertEqual(status, 429)
            self.assertIn("error", parsed)
            # 429 denials are also audited with the ':denied' suffix.
            denied = [e for e in self.audit.entries()
                      if e["action"] == "invoke:denied" and e["actor"] == "bob"]
            self.assertTrue(denied)
        finally:
            # Restore headroom for other tests sharing this server.
            self.store.set_quota("bob", 10 ** 9, _admin_user())

    def test_sessions_requests_and_usage_over_http(self):
        """Core 8+5+4: POST /sessions -> 201, a completion into the
        session appends its turn, GET /sessions/{id} and
        GET /requests/{id} read them back, GET /usage/{owner}
        aggregates the actor's usage."""
        status, _, session = self.request(
            "POST", "/sessions", headers=BOB, body={"title": "http chat"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(session["id"].startswith("ses-"))

        status, _, record = self.request(
            "POST", "/v1/completions", headers=BOB,
            body={"model": self._model_name(), "prompt": "abcd",
                  "session_id": session["id"]},
        )
        self.assertEqual(status, 201)

        status, _, fetched = self.request(
            "GET", "/sessions/%s" % session["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(fetched["turns"]), 1)

        status, _, got = self.request(
            "GET", "/requests/%s" % record["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], record["id"])

        status, _, usage = self.request("GET", "/usage/bob", headers=BOB)
        self.assertEqual(status, 200)
        self.assertEqual(usage["owner"], "bob")
        self.assertGreaterEqual(usage["requests"], 1)

        # Another member reading bob's usage is denied by the store.
        status, _, parsed = self.request("GET", "/usage/bob", headers={
            "X-User": "dave", "X-Role": "member"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)


def _admin_user():
    from aigateway.access import User
    return User("alice", "admin")


class TestKeysPolicyEvalAuditEndpoints(ServiceBase):
    """Core functions 8, 9, 6, 7, 10: keys, policy, eval, audit."""

    def test_key_endpoints_secret_once_and_scoped_list(self):
        """Core 8+9: POST /keys -> 201 returning the secret once;
        GET /keys lists keys without any secret material, scoped to
        the caller for non-admins."""
        status, _, key = self.request(
            "POST", "/keys", headers=BOB, body={"owner": "bob"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(key["secret"])
        status, _, payload = self.request("GET", "/keys", headers=BOB)
        self.assertEqual(status, 200)
        for listed in payload["keys"]:
            self.assertNotIn("secret", listed)
            self.assertNotIn("secret_hash", listed)
        self.assertNotIn(key["secret"], json.dumps(payload))

    def test_policy_rule_delete_over_http(self):
        """Core 8+6: DELETE /policy/rules/{id} removes the rule
        (200, the removed dict); a member may not (403)."""
        status, _, rule = self.request(
            "POST", "/policy/rules", headers=ALICE,
            body={"scope": "input", "kind": "term", "value": " ephemeral"},
        )
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "DELETE", "/policy/rules/%s" % rule["id"], headers=BOB
        )
        self.assertEqual(status, 403)
        status, _, removed = self.request(
            "DELETE", "/policy/rules/%s" % rule["id"], headers=ALICE
        )
        self.assertEqual(status, 200)
        self.assertEqual(removed["id"], rule["id"])
        status, _, payload = self.request("GET", "/policy/rules", headers=BOB)
        self.assertEqual(status, 200)
        self.assertNotIn(rule["id"], [r["id"] for r in payload["rules"]])

    def test_eval_endpoints(self):
        """Core 8+7: POST /eval/datasets -> 201, POST
        /eval/datasets/{id}/runs -> 201 with the scored run, GET
        /eval/runs/{id} reads it back."""
        self.create_model("eval-echo")
        status, _, dataset = self.request(
            "POST", "/eval/datasets", headers=BOB,
            body={"name": "ds",
                  "cases": [{"prompt": "hi", "expected": "hi"}]},
        )
        self.assertEqual(status, 201)
        status, _, run = self.request(
            "POST", "/eval/datasets/%s/runs" % dataset["id"], headers=BOB,
            body={"model": "eval-echo"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(run["score"], 1.0)
        status, _, got = self.request(
            "GET", "/eval/runs/%s" % run["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], run["id"])
        status, _, payload = self.request("GET", "/eval/datasets", headers=BOB)
        self.assertEqual(status, 200)
        self.assertIn(dataset["id"], [d["id"] for d in payload["datasets"]])

    def test_audit_endpoint_admin_only_and_denied_suffix(self):
        """Core 8+10 (AU-6): GET /audit is admin-only (member/viewer
        -> 403); denied attempts (403 here, 401 below) appear in the
        trail with the ':denied' suffix, and successful audit_read
        is recorded by the service layer."""
        for headers in (BOB, CAROL):
            status, _, parsed = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
            self.assertIn("error", parsed)
        status, _, _ = self.request(
            "GET", "/models", headers={"X-User": "mallory", "X-Role": "admin"}
        )
        self.assertEqual(status, 401)

        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        denied = [e for e in entries if str(e["action"]).endswith(":denied")]
        self.assertTrue(denied, "expected :denied audit entries")
        actions = [e["action"] for e in entries]
        self.assertIn("audit_read", actions)
        for entry in entries:
            for key in ("ts", "actor", "action", "target"):
                self.assertIn(key, entry)


if __name__ == "__main__":
    unittest.main()
