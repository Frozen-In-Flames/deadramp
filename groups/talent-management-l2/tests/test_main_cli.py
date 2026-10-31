"""CLI: ``python -m talentmgmt serve`` answers /health.

Traces to: UNION-SPEC.md "Implementation contract" (__main__.py)
— the module entry point starts the HTTP service with the demo
user registry on the requested port.
"""

import http.client
import json
import os
import subprocess
import sys
import time
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")

PORT = 8891


class TestMainCli(unittest.TestCase):
    """The CLI starts a working server subprocess."""

    def test_serve_answers_health(self):
        """CLI: the serve subcommand binds the port and answers
        GET /health with the ok payload."""
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR
        proc = subprocess.Popen(
            [sys.executable, "-m", "talentmgmt", "serve",
             "--port", str(PORT)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, text=True)
        try:
            deadline = time.time() + 15
            body = None
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", PORT,
                                                      timeout=2)
                    conn.request("GET", "/health")
                    response = conn.getresponse()
                    body = json.loads(response.read())
                    conn.close()
                    if response.status == 200:
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertEqual(body, {"status": "ok"})
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
