"""CLI entry point.

Traces to: the UNION-SPEC implementation contract for
``legalpol/__main__.py`` — ``python -m legalpol serve`` with demo
users alice=admin, bob=member, carol=viewer and default port 8799
answers ``GET /health`` with ``{"status": "ok"}`` and no auth.
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestMainCli(unittest.TestCase):
    """Contract: the module CLI serves /health on a live port."""

    def test_serve_answers_health(self):
        """CLI: a `serve` subprocess answers /health with 200 ok."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR
        proc = subprocess.Popen(
            [sys.executable, "-m", "legalpol", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        try:
            deadline = time.time() + 15
            body = None
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port,
                                                      timeout=2)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    raw = resp.read()
                    conn.close()
                    if resp.status == 200:
                        body = json.loads(raw)
                        break
                except OSError:
                    time.sleep(0.1)
            self.assertEqual(body, {"status": "ok"})
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
