"""CLI: ``python -m sysadmin serve`` starts and answers /health.
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
_SRC_DIR = os.path.join(os.path.dirname(_TESTS_DIR), "src")


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
        env["PYTHONPATH"] = _SRC_DIR
        proc = subprocess.Popen(
            [sys.executable, "-m", "sysadmin", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            deadline = time.time() + 15
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
                    time.sleep(0.2)
            self.assertEqual(payload, {"status": "ok"})
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
