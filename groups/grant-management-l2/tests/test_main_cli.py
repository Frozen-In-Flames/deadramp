"""Core: CLI entry point. Traces to UNION-SPEC implementation
contract: ``python -m grants serve`` starts the service with the
documented demo users."""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestCommandLine(unittest.TestCase):
    def test_serve_starts_and_answers_health(self):
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(GROUP_ROOT, "src")
        proc = subprocess.Popen(
            [sys.executable, "-m", "grants", "serve", "--port", str(port)],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            body = None
            for _ in range(50):
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port,
                                                      timeout=2)
                    conn.request("GET", "/health")
                    response = conn.getresponse()
                    body = json.loads(response.read())
                    conn.close()
                    break
                except OSError:
                    time.sleep(0.1)
            self.assertEqual(body, {"status": "ok"})
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
