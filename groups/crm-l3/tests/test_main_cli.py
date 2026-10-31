"""CLI tests: ``python -m crm serve`` as a subprocess.

Traces to: Core 10 (REST API) -- the documented entry point boots
with demo users alice/bob/carol and answers /health.
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import unittest

import crm_helpers as H

SRC = H._SRC_DIR
GROUP_ROOT = H._GROUP_ROOT


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestMainCli(unittest.TestCase):
    """Core 10: python -m crm serve subprocess."""

    def test_serve_boots_and_answers_health(self):
        """Core 10: the CLI starts the service with demo users and
        /health answers ok."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC
        proc = subprocess.Popen(
            [sys.executable, "-m", "crm", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.time() + 15
            body = None
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    raw = resp.read()
                    conn.close()
                    if resp.status == 200:
                        body = json.loads(raw.decode("utf-8"))
                        break
                except OSError:
                    time.sleep(0.2)
            self.assertEqual(body, {"status": "ok"})
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_no_command_prints_help(self):
        """Core 10: running with no subcommand prints help, exit 2."""
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC
        proc = subprocess.run(
            [sys.executable, "-m", "crm"], cwd=GROUP_ROOT, env=env,
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("serve", proc.stdout)


class TestCommandLineUplifts(unittest.TestCase):
    """Core 10 [L3]: the CLI serves dana=auditor and accepts the
    AC-7 lockout flags."""

    def test_serve_with_auditor_and_lockout_flags(self):
        """[L3] AC-5/AC-7: serve --max-failed-logins/--lockout-seconds
        boots; dana (auditor) can GET /audit but not /accounts."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC
        proc = subprocess.Popen(
            [sys.executable, "-m", "crm", "serve",
             "--host", "127.0.0.1", "--port", str(port),
             "--max-failed-logins", "3", "--lockout-seconds", "300"],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.time() + 15
            up = False
            while time.time() < deadline:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    resp.read()
                    conn.close()
                    if resp.status == 200:
                        up = True
                        break
                except OSError:
                    time.sleep(0.2)
            self.assertTrue(up, "server did not come up")

            def get(path, user, role):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", path,
                             headers={"X-User": user, "X-Role": role})
                resp = conn.getresponse()
                resp.read()
                status = resp.status
                conn.close()
                return status

            self.assertEqual(get("/audit", "dana", "auditor"), 200)
            self.assertEqual(get("/accounts", "dana", "auditor"), 403)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
