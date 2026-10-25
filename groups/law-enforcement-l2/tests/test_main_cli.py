"""CLI entry point: ``python -m lawenf serve``.

Traces to: the contract's CLI (demo users alice/bob/carol) -- the
subprocess boots, answers /health, serves an authenticated request,
and shuts down on terminate.
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
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestMainCli(unittest.TestCase):
    """Contract: the module CLI runs the service with demo users."""

    def test_serve_boots_and_answers(self):
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR
        proc = subprocess.Popen(
            [sys.executable, "-m", "lawenf", "serve", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        try:
            deadline = time.time() + 20
            body = None
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    body = json.loads(resp.read())
                    conn.close()
                    break
                except OSError:
                    time.sleep(0.25)
            self.assertEqual(body, {"status": "ok"})

            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/matters",
                         body=json.dumps({"matter_ref": "CLI-REF-1"}),
                         headers={"X-User": "bob", "X-Role": "member"})
            resp = conn.getresponse()
            created = json.loads(resp.read())
            conn.close()
            self.assertEqual(resp.status, 201)
            self.assertEqual(created["matter_ref"], "CLI-REF-1")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
