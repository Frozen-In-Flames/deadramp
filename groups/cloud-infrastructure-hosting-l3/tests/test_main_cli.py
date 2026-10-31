"""CLI entry point: parser shape and argument validation.

The first class is carried verbatim from the founding L2 build;
the second pins the High-tier serve flags [L3].
"""

import unittest

from cloudinfra.__main__ import build_parser, main


class TestMainCli(unittest.TestCase):
    def test_parser_defaults(self):
        args = build_parser().parse_args(
            ["serve"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8819)
        self.assertIsNone(args.audit_log)

    def test_no_command_returns_2(self):
        self.assertEqual(main([]), 2)

    def test_certfile_and_keyfile_must_come_together(self):
        with self.assertRaises(SystemExit):
            main(["serve", "--certfile", "cert.pem"])


class TestMainCliLockoutFlags(unittest.TestCase):
    """[L3] AC-7: the lockout serve flags exist with the precedent
    defaults (3 consecutive failures, 300 seconds)."""

    def test_lockout_flag_defaults(self):
        args = build_parser().parse_args(["serve"])
        self.assertEqual(args.max_failed_logins, 3)
        self.assertEqual(args.lockout_seconds, 300)

    def test_lockout_flags_parse(self):
        args = build_parser().parse_args(
            ["serve", "--max-failed-logins", "5",
             "--lockout-seconds", "60"])
        self.assertEqual(args.max_failed_logins, 5)
        self.assertEqual(args.lockout_seconds, 60)


if __name__ == "__main__":
    unittest.main()
