"""CLI smoke test for ``python -m devtools``.

Traces to: contract for ``devtools/__main__.py``:
`python -m devtools serve --host 127.0.0.1 --port ...` with demo users
alice=admin, bob=developer, carol=viewer, dana=auditor. L3 adds the
AC-7 flags `--max-failed-logins` / `--lockout-seconds`; the startup
line ends "dana=auditor)".
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
    """CLI: module entry point serves the demo users."""

    def test_serve_starts_and_answers(self):
        """CLI: `python -m devtools serve` becomes healthy and answers alice (admin) on /audit and carol (viewer) on /projects."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "devtools", "serve",
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
                    self.fail("devtools CLI exited early (%s): %s" % (proc.returncode, output[:2000]))
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
            status, _ = _get(port, "/projects", {"X-User": "carol", "X-Role": "viewer"})
            self.assertEqual(status, 200)
            status, _ = _get(port, "/audit", {"X-User": "bob", "X-Role": "developer"})
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


class TestCommandLineUplifts(unittest.TestCase):
    """L3 High uplifts at the CLI: demo user dana=auditor (AC-5), the
    startup line naming her, and the AC-7 lockout flags."""

    def test_parser_accepts_lockout_flags(self):
        """AC-7: build_parser() accepts --max-failed-logins /
        --lockout-seconds (parse-level), with defaults 3 / 300
        matching make_server's AC-7 defaults."""
        sys.path.insert(0, SRC_DIR)
        from devtools.__main__ import build_parser

        args = build_parser().parse_args(
            ["serve", "--max-failed-logins", "2", "--lockout-seconds", "60"]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.max_failed_logins, 2)
        self.assertEqual(args.lockout_seconds, 60)
        defaults = build_parser().parse_args(["serve"])
        self.assertEqual(defaults.max_failed_logins, 3)
        self.assertEqual(defaults.lockout_seconds, 300)

    def test_startup_line_names_dana_and_flags_plumb_through(self):
        """AC-5/AC-7: the startup line ends "dana=auditor)"; dana can
        read the audit log; with --max-failed-logins 2, bob locks
        after two bad-role attempts and the correct role gets 403."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "devtools", "serve",
             "--host", "127.0.0.1", "--port", str(port),
             "--max-failed-logins", "2", "--lockout-seconds", "60"],
            cwd=GROUP_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        output = ""
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail("devtools CLI exited early (%s): %s" % (proc.returncode, output[:2000]))
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

            for _ in range(2):
                status, _ = _get(port, "/projects", {"X-User": "bob", "X-Role": "admin"})
                self.assertEqual(status, 401)
            status, _ = _get(port, "/projects", {"X-User": "bob", "X-Role": "developer"})
            self.assertEqual(status, 403)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            if proc.stdout is not None:
                output = proc.stdout.read() or output
                proc.stdout.close()
        self.assertIn(
            "(demo users: alice=admin, bob=developer, carol=viewer, dana=auditor)",
            output,
        )


if __name__ == "__main__":
    unittest.main()
