"""CLI smoke test for ``python -m health``.

Traces to: contract for ``health/__main__.py``:
`python -m health serve --host 127.0.0.1 --port 8792` with demo users
alice=admin, bob=clinician, carol=member, dana=auditor.
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
    """CLI helper -- find a free local port for the subprocess server."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port, path, headers=None):
    """CLI helper -- GET helper against the subprocess server."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    status = resp.status
    conn.close()
    return status, body


class TestCommandLineServe(unittest.TestCase):
    """CLI: module entry point serves the four demo users."""

    def test_serve_starts_and_answers(self):
        """CLI: `python -m health serve` becomes healthy and answers alice (admin) and dana (auditor) on /audit, carol (member) on /programs."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "health", "serve",
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
                    self.fail("health CLI exited early (%s): %s" % (proc.returncode, output[:2000]))
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
            status, _ = _get(port, "/audit", {"X-User": "dana", "X-Role": "auditor"})
            self.assertEqual(status, 200)
            status, _ = _get(port, "/programs", {"X-User": "carol", "X-Role": "member"})
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

    def test_no_subcommand_returns_2(self):
        """CLI: `python -m health` with no subcommand prints help and returns 2."""
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "health"],
            cwd=GROUP_ROOT, env=env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("serve", proc.stdout)


class TestCommandLineUplifts(unittest.TestCase):
    """CLI [L3]: the CLI serves dana=auditor (audit_read only) and
    accepts the AC-7 lockout flags."""

    def test_serve_with_auditor_and_lockout_flags(self):
        """[L3] AC-5/AC-7: serve --max-failed-logins/--lockout-seconds
        boots; dana (auditor) can GET /audit but not /programs."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "health", "serve",
             "--host", "127.0.0.1", "--port", str(port),
             "--max-failed-logins", "3", "--lockout-seconds", "300"],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail("health CLI exited early (%s): %s" % (proc.returncode, output[:2000]))
                try:
                    status, _ = _get(port, "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")
            status, _ = _get(port, "/audit", {"X-User": "dana", "X-Role": "auditor"})
            self.assertEqual(status, 200)
            status, _ = _get(port, "/programs", {"X-User": "dana", "X-Role": "auditor"})
            self.assertEqual(status, 403)
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
