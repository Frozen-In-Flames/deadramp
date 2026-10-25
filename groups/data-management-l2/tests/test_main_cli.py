"""CLI smoke test for ``python -m datamgmt``.

Traces to: contract for ``datamgmt/__main__.py``:
`python -m datamgmt serve --port 8792` (default port 8792) prints a
listening line naming the demo users alice=admin, bob=steward,
carol=viewer.
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
    """Core: CLI -- find a free local port for the subprocess server."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port, path, headers=None):
    """Core: CLI -- GET helper against the subprocess server."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    status = resp.status
    conn.close()
    return status, body


class TestCommandLineServe(unittest.TestCase):
    """Core: REST API -- module entry point serves demo users."""

    def test_serve_starts_and_answers(self):
        """Core: CLI. `python -m datamgmt serve --port <free>` becomes healthy and answers alice (admin) on /audit and carol (viewer) on /datasets."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "datamgmt", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail("datamgmt CLI exited early (%s): %s" % (proc.returncode, output[:2000]))
                try:
                    status, _ = _get(port, "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")
            status, _ = _get(port, "/audit", {"X-User": "alice", "X-Role": "admin"})
            self.assertEqual(status, 200)
            status, _ = _get(port, "/datasets", {"X-User": "carol", "X-Role": "viewer"})
            self.assertEqual(status, 200)
            status, _ = _get(port, "/datasets", {"X-User": "bob", "X-Role": "steward"})
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
