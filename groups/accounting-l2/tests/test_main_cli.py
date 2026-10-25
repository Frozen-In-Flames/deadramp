"""CLI smoke test for ``python -m accounting``.

Traces to: UNION-SPEC Implementation contract for
``accounting/__main__.py``: `python -m accounting serve --host --port
[--audit-log PATH] [--certfile --keyfile]` with demo users
alice=admin, bob=member, carol=viewer.
"""

import http.client
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
    """Core 11: API access — the module entry point serves demo users."""

    def test_serve_starts_and_answers_an_authenticated_request(self):
        """Core 11: API access. `python -m accounting serve` starts
        an HTTP service that becomes healthy on /health and answers an
        authenticated request from a demo user (alice, admin, reading
        the audit log and her book list)."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "accounting", "serve",
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
                        "accounting CLI exited early (%s): %s"
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

            status, _ = _get(port, "/books",
                             {"X-User": "alice", "X-Role": "admin"})
            self.assertEqual(status, 200)
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
