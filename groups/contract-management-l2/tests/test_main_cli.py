"""CLI: ``python -m contractmgmt serve`` answers /health.

Traces to: UNION-SPEC.md implementation contract for
``contractmgmt/__main__.py`` — the module entry point starts the
service with the documented demo users.
"""

import http.client
import json
import os
import re
import subprocess
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")


class TestMainCli(unittest.TestCase):
    """The CLI subprocess serves /health on an ephemeral port."""

    def test_cli_serve_health(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR
        proc = subprocess.Popen(
            [sys.executable, "-m", "contractmgmt", "serve",
             "--host", "127.0.0.1", "--port", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, text=True)
        try:
            line = proc.stdout.readline()
            match = re.search(r":(\d+) ", line)
            self.assertIsNotNone(match, line)
            port = int(match.group(1))
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request("GET", "/health")
            response = conn.getresponse()
            body = json.loads(response.read())
            conn.close()
            self.assertEqual(response.status, 200)
            self.assertEqual(body, {"status": "ok"})
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
