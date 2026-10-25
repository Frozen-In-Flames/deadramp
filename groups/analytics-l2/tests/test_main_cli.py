"""CLI smoke test for ``python -m analytics``.

Traces to: UNION-SPEC Implementation contract for
``analytics/__main__.py``: `python -m analytics serve --host --port
[--audit-log PATH] [--certfile --keyfile]` with demo users
alice=admin, bob=analyst, carol=viewer.
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(GROUP_ROOT, "src")


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    status = resp.status
    conn.close()
    return status, body


class TestCommandLineServe(unittest.TestCase):
    """Core: API access — the module entry point serves the demo users."""

    def test_serve_starts_and_enforces_demo_roles(self):
        """Core: API access. `python -m analytics serve` starts an HTTP
        service where alice (admin) can read the audit log and carol
        (viewer) cannot create datasets."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "analytics", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
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
                        "analytics CLI exited early (%s): %s"
                        % (proc.returncode, output[:2000])
                    )
                try:
                    status, _ = _get(port, "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")

            status, _ = _get(port, "/audit",
                             {"X-User": "alice", "X-Role": "admin"})
            self.assertEqual(status, 200)

            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request(
                "POST", "/datasets",
                body=json.dumps({"name": "cli-denied", "format": "json",
                                 "data": "[]"}),
                headers={"X-User": "carol", "X-Role": "viewer",
                         "Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            resp.read()
            conn.close()
            self.assertEqual(resp.status, 403)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            if proc.stdout is not None:
                proc.stdout.close()


if __name__ == "__main__":
    unittest.main()
