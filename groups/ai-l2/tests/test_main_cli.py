"""CLI smoke test for ``python -m aigateway``.

Traces to: UNION-SPEC Implementation contract for
``aigateway/__main__.py``: `python -m aigateway serve --host --port
[--audit-log PATH] [--zero-persistence] [--certfile --keyfile]` with
demo users alice=admin, bob=member, carol=viewer.
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import unittest

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(GROUP_ROOT, "src")


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _request(port, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    payload = json.dumps(body) if body is not None else None
    hdrs = dict(headers or {})
    if payload is not None:
        hdrs.setdefault("Content-Type", "application/json")
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    status = resp.status
    conn.close()
    return status, raw


class TestCommandLineServe(unittest.TestCase):
    """Core function 8: API access — the module entry point serves
    the demo users, with and without --zero-persistence."""

    def _serve(self, extra_args=()):
        import time
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "aigateway", "serve",
             "--host", "127.0.0.1", "--port", str(port)] + list(extra_args),
            cwd=GROUP_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail(
                        "aigateway CLI exited early (%s): %s"
                        % (proc.returncode, output[:2000])
                    )
                try:
                    status, _ = _request(port, "GET", "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")
            yield port
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            if proc.stdout is not None:
                proc.stdout.close()

    def test_serve_starts_and_answers_demo_user_requests(self):
        """Core 8: `python -m aigateway serve` starts an HTTP service
        that becomes healthy, registers a model as alice (admin),
        completes a stub invocation as bob (member), and serves the
        audit log to alice."""
        for port in self._serve():
            alice = {"X-User": "alice", "X-Role": "admin"}
            bob = {"X-User": "bob", "X-Role": "member"}
            status, raw = _request(
                port, "POST", "/models", headers=alice,
                body={"name": "cli-echo", "responder": "echo"},
            )
            self.assertEqual(status, 201, raw[:500])
            status, raw = _request(
                port, "POST", "/v1/completions", headers=bob,
                body={"model": "cli-echo", "prompt": "hello cli"},
            )
            self.assertEqual(status, 201, raw[:500])
            record = json.loads(raw.decode("utf-8"))
            self.assertEqual(record["output"], "hello cli")
            self.assertIs(record["reference_stub"], True)
            status, _ = _request(port, "GET", "/audit", headers=alice)
            self.assertEqual(status, 200)

    def test_serve_zero_persistence_flag_withholds_content(self):
        """Core 5+8: `serve --zero-persistence` runs the store in
        zero-persistence mode — a completion over HTTP returns
        prompt/output as None with content_withheld true."""
        for port in self._serve(extra_args=("--zero-persistence",)):
            alice = {"X-User": "alice", "X-Role": "admin"}
            bob = {"X-User": "bob", "X-Role": "member"}
            status, _ = _request(
                port, "POST", "/models", headers=alice,
                body={"name": "zp-echo", "responder": "echo"},
            )
            self.assertEqual(status, 201)
            status, raw = _request(
                port, "POST", "/v1/completions", headers=bob,
                body={"model": "zp-echo", "prompt": "ephemeral words"},
            )
            self.assertEqual(status, 201)
            record = json.loads(raw.decode("utf-8"))
            self.assertIsNone(record["prompt"])
            self.assertIsNone(record["output"])
            self.assertIs(record["content_withheld"], True)
            self.assertEqual(record["status"], "completed")

    def test_no_command_prints_help_and_returns_nonzero(self):
        """__main__ contract: running the module without `serve`
        prints usage help instead of starting a server."""
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-m", "aigateway"],
            cwd=GROUP_ROOT, env=env, capture_output=True, text=True,
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("serve", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
