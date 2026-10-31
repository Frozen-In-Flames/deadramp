"""CLI entry point: parser shape and argument validation."""

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


if __name__ == "__main__":
    unittest.main()
