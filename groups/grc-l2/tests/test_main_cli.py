"""CLI entry-point tests: ``python -m grc serve``.

Traces to: Core function 8 (REST API) as launched by the command-line
entry point, with the documented demo identities alice=admin,
bob=member, carol=viewer (hooks, not an IdP; IA-2).
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")


def _free_port():
    """An ephemeral localhost port for the subprocess server."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port, path, headers=None):
    """One GET against the subprocess server; returns (status, parsed)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    raw = resp.read()
    status = resp.status
    conn.close()
    try:
        parsed = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        parsed = None
    return status, parsed


class TestMainCli(unittest.TestCase):
    """Core 8: the CLI serves the API with the demo users."""

    def test_serve_answers_health_systems_posture_and_audit(self):
        """Core 8. `python -m grc serve` becomes healthy on /health
        (no auth) and answers authenticated requests from the demo
        users: carol (viewer) reading systems, bob (member) reading
        posture, alice (admin) reading the audit log — while audit
        stays admin-only and a role mismatch is 401."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "grc", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=_GROUP_ROOT,
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
                        "grc CLI exited early (%s): %s"
                        % (proc.returncode, output[:2000])
                    )
                try:
                    status, parsed = _get(port, "/health")
                    if status == 200:
                        self.assertEqual(parsed, {"status": "ok"})
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")

            status, parsed = _get(
                port, "/systems", {"X-User": "carol", "X-Role": "viewer"}
            )
            self.assertEqual(status, 200)
            self.assertEqual(parsed, {"systems": []})

            status, parsed = _get(
                port, "/posture", {"X-User": "bob", "X-Role": "member"}
            )
            self.assertEqual(status, 200)
            self.assertEqual(parsed["frameworks"]["controls_total"], 21)

            status, _ = _get(port, "/audit", {"X-User": "bob", "X-Role": "member"})
            self.assertEqual(status, 403)
            status, parsed = _get(
                port, "/audit", {"X-User": "alice", "X-Role": "admin"}
            )
            self.assertEqual(status, 200)
            self.assertIn("entries", parsed)

            # The demo registry is enforced: carol claiming admin is a
            # role mismatch -> 401.
            status, _ = _get(port, "/audit", {"X-User": "carol", "X-Role": "admin"})
            self.assertEqual(status, 401)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            if proc.stdout is not None:
                proc.stdout.close()

    def test_no_subcommand_prints_help_and_returns_2(self):
        """Core 8. `python -m grc` without `serve` prints usage and
        exits 2 (the house pattern)."""
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR
        result = subprocess.run(
            [sys.executable, "-m", "grc"],
            capture_output=True, env=env, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("serve", result.stdout)


if __name__ == "__main__":
    unittest.main()
