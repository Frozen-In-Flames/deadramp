"""CLI: ``python -m mdm serve`` answers /health (implementation contract)."""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

import mdm_helpers as H  # noqa: F401  (puts src/ on the path)

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestMainCli(unittest.TestCase):
    def test_serve_answers_health(self):
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(GROUP_ROOT, "src")
        proc = subprocess.Popen(
            [sys.executable, "-m", "mdm", "serve", "--port", str(port)],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.time() + 20
            payload = None
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port,
                                                      timeout=2)
                    conn.request("GET", "/health")
                    response = conn.getresponse()
                    payload = json.loads(response.read())
                    conn.close()
                    break
                except OSError:
                    time.sleep(0.25)
            self.assertEqual(payload, {"status": "ok"})
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
