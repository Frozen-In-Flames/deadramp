"""CLI smoke test for ``python -m collab``.

Traces to: UNION-SPEC Implementation contract for
``collab/__main__.py``: `python -m collab serve --host --port
[--audit-log PATH] [--certfile --keyfile]` with demo users
alice=admin, bob=member, carol=viewer, dana=auditor. L3 adds the
AC-7 flags `--max-failed-logins` / `--lockout-seconds`; the startup
line reads "(demo users: alice=admin, bob=member, carol=viewer,
dana=auditor)".
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
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    status = resp.status
    conn.close()
    return status, body


class TestCommandLineServe(unittest.TestCase):
    """Core: API access — the module entry point serves the demo users."""

    def test_serve_starts_and_answers_an_authenticated_request(self):
        """Core: API access. `python -m collab serve` starts an HTTP
        service that becomes healthy on /health and answers an
        authenticated request from a demo user (alice, admin, reading
        the audit log and her workspace list)."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "collab", "serve",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=GROUP_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail(
                        "collab CLI exited early (%s): %s"
                        % (proc.returncode, output[:2000])
                    )
                try:
                    status, _ = _get(port, "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")

            status, _ = _get(port, "/audit",
                             {"X-User": "alice", "X-Role": "admin"})
            self.assertEqual(status, 200)

            status, _ = _get(port, "/workspaces",
                             {"X-User": "alice", "X-Role": "admin"})
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


class TestCommandLineUplifts(unittest.TestCase):
    """L3 High uplifts at the CLI: demo user dana=auditor (AC-5), the
    startup line naming her, and the AC-7 lockout flags."""

    def test_parser_accepts_lockout_flags(self):
        """AC-7: build_parser() accepts --max-failed-logins /
        --lockout-seconds (parse-level), with defaults 3 / 300
        matching make_server's AC-7 defaults."""
        sys.path.insert(0, SRC_DIR)
        from collab.__main__ import build_parser

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
        """AC-5/AC-7: the startup line reads "(demo users:
        alice=admin, bob=member, carol=viewer, dana=auditor)"; dana
        can read the audit log; with --max-failed-logins 2, bob locks
        after two bad-role attempts and the correct role gets 403."""
        port = _free_port()
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(
            [sys.executable, "-m", "collab", "serve",
             "--host", "127.0.0.1", "--port", str(port),
             "--max-failed-logins", "2", "--lockout-seconds", "60"],
            cwd=GROUP_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = ""
        try:
            deadline = time.time() + 20
            healthy = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    self.fail(
                        "collab CLI exited early (%s): %s"
                        % (proc.returncode, output[:2000])
                    )
                try:
                    status, _ = _get(port, "/health")
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(0.25)
            self.assertTrue(healthy, "server did not become healthy")

            status, _ = _get(port, "/audit",
                             {"X-User": "dana", "X-Role": "auditor"})
            self.assertEqual(status, 200)

            for _ in range(2):
                status, _ = _get(port, "/workspaces",
                                 {"X-User": "bob", "X-Role": "admin"})
                self.assertEqual(status, 401)
            status, _ = _get(port, "/workspaces",
                             {"X-User": "bob", "X-Role": "member"})
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
            "(demo users: alice=admin, bob=member, carol=viewer, dana=auditor)",
            output,
        )


if __name__ == "__main__":
    unittest.main()
